"""
agent.py - Sonar agent.

Single agent that handles UX, intent clarification, request construction,
tool execution, and response formatting. Mirrors ConnectChat architecture.
"""

import asyncio
import uuid

from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langfuse.langchain import CallbackHandler

from .config import Config

from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

def _load_system_prompt(config: Config) -> str:
    """Load system prompt from YAML file."""
    import yaml

    with open(config.prompts_file, "r") as f:
        prompts = yaml.safe_load(f)
    return prompts["system_prompt"]


class SonarAgent:
    """
    Single-agent conversational assistant for querying the Whale Hotline API.

    Mirrors ConnectChat architecture as a baseline for architectural exploration.

    Example:
        async with SonarAgent() as agent:
            result = await agent.agent.ainvoke(
                {"messages": [{"role": "user", "content": "Any J pod sightings?"}]},
                {"configurable": {"thread_id": "user-123"}}
            )
    """

    def __init__(self, config: Config | None = None, thread_id: str = "default"):
        self.config = config or Config.from_env()
        self.thread_id = thread_id

        model = ChatGroq(
            model=self.config.model_id,
            temperature=self.config.temperature,
        )

        system_prompt = _load_system_prompt(self.config)

        self.agent = create_agent(
            model=model,

            server_path=Path(__file__).parent / "server.py"
            mcp_client = MultiServerMCPClient({
                "sonar": {
                    "command": "python",
                    "args": [str(server_path)],
                    "transport": "stdio",
                }
            })
            tools = await mcp_client.get_tools()

            system_prompt=system_prompt,
            middleware=[
                ToolCallLimitMiddleware(
                    run_limit=self.config.max_tool_calls_per_run,
                    exit_behavior="end",
                ),
                SummarizationMiddleware(
                    model=model,
                    summary_prompt="Summarize the conversation including any species or sightings discussed, filters used, and results returned. Keep any important context for follow-up questions.",
                ),
            ],
            checkpointer=InMemorySaver(),
        )

        # Langfuse tracing — optional, skipped if keys not set
        self._langfuse_handler = None
        if self.config.langfuse_public_key and self.config.langfuse_secret_key:
            self._langfuse_handler = CallbackHandler()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def chat_loop(self):
        """Interactive CLI chat loop. Run via scripts/chat.py."""
        print("   Sonar — Chatbot for marine mammal sightings data from iNaturalist")
        print("   Data: https://www.inaturalist.org")
        print(f"   Thread: {self.thread_id}")
        print("   Commands: 'exit' to quit, 'new' to start a new thread")
        print("-" * 60 + "\n")

        config = {"configurable": {"thread_id": self.thread_id}}

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You: ")
                )
                user_input = user_input.strip()

                if user_input.lower() in {"exit", "quit"}:
                    print("\nGoodbye!")
                    break

                if user_input.lower() == "new":
                    self.thread_id = str(uuid.uuid4())
                    config = {"configurable": {"thread_id": self.thread_id}}
                    if self._langfuse_handler:
                        self._langfuse_handler = CallbackHandler()
                    print(f"\n[New conversation: {self.thread_id}]\n")
                    continue

                if not user_input:
                    continue

                callbacks = [self._langfuse_handler] if self._langfuse_handler else []
                result = await self.agent.ainvoke(
                    {"messages": [{"role": "user", "content": user_input}]},
                    {**config, "callbacks": callbacks},
                )

                reply = result["messages"][-1].content

                # Print response
                print(f"\nAssistant: {reply}\n")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 🐋")
                break
            except Exception as e:
                import traceback
                traceback.print_exc()

def main():
    asyncio.run(async_main())