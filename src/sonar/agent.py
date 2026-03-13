"""
agent.py - Sonar agent.

Single agent that handles UX, intent clarification, request construction,
tool execution, and response formatting. Mirrors ConnectChat architecture.
"""

import asyncio
import uuid
from pathlib import Path

import yaml
from langchain.agents import create_agent
from langchain.agents.middleware import (
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from langfuse.langchain import CallbackHandler
from langgraph.checkpoint.memory import InMemorySaver

from .config import Config


def _load_system_prompt(config: Config) -> str:
    """Load system prompt from YAML file."""
    with open(config.prompts_file, "r") as f:
        prompts = yaml.safe_load(f)
    return prompts["system_prompt"]


class SonarAgent:
    """
    Single-agent conversational assistant for marine mammal sightings via iNaturalist.

    Mirrors ConnectChat architecture as a baseline for architectural exploration.
    Tools are loaded from the MCP server (server.py) via MultiServerMCPClient.

    Use the classmethod entrypoint:
        await SonarAgent.run()
    """

    def __init__(self, config: Config, tools: list, thread_id: str = "default"):
        self.config = config
        self.thread_id = thread_id

        model = ChatGroq(
            model=self.config.model_id,
            temperature=self.config.temperature,
        )

        system_prompt = _load_system_prompt(self.config)

        self.agent = create_agent(
            model=model,
            tools=tools,
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

    @classmethod
    async def run(cls, config: Config | None = None):
        """
        Async entry point — handles MCP client setup then enters chat loop.

        Async is required here because launching the MCP server subprocess
        and completing the tool handshake is I/O. Everything after this
        is synchronous object construction.

        Phase 1 (stdio): server.py launched as a local subprocess.
        Phase 3+ (http): swap transport to point at remote HF Spaces URL.
        """
        config = config or Config.from_env()

        # Launch MCP server subprocess and fetch tools
        server_path = Path(__file__).parent / "server.py"
        mcp_client = MultiServerMCPClient({
            "sonar": {
                "command": "python",
                "args": [str(server_path)],
                "transport": "stdio",
            }
        })
        tools = await mcp_client.get_tools()

        agent = cls(config=config, tools=tools)
        await agent.chat_loop()

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
                print(f"\nAssistant: {reply}\n")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 🐋")
                break
            except Exception as e:
                print(f"\nError: {e}\n")


async def async_main():
    await SonarAgent.run()


def main():
    asyncio.run(async_main())