"""
config.py - Sonar configuration.

Required environment variables:
    MODEL_ID                Model identifier, e.g. llama-3.3-70b-versatile

Optional environment variables (defaults shown):
    TEMPERATURE             Model temperature (default: 0)
    MAX_TOOL_CALLS_PER_RUN  Tool call limit per invocation (default: 3)
    PROMPTS_FILE            Path to prompts YAML, relative to project root

Note: GROQ_API_KEY is required but read directly by ChatGroq — not managed here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _require(name: str) -> str:
    """Get a required environment variable or raise clearly."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: {name}. "
            f"Check your .env file or shell environment."
        )
    return value


class Config(BaseModel):
    # Model
    model_id: str = Field(default_factory=lambda: _require("MODEL_ID"))
    temperature: float = Field(default=0)

    # Agent behavior
    max_tool_calls_per_run: int = Field(default=3)

    # Paths (relative to ect root)
    prompts_file: str = Field(default="src/sonar/prompts/system.yaml")

    @classmethod
    def project_root(cls) -> Path:
        """Project root - two levels up from this file (src/sonar/config.py)."""
        return Path(__file__).parent.parent.parent

    @classmethod
    def from_env(cls) -> "Config":
        """
        Build Config from environment variables.
        Optional vars fall back to field defaults if not set.

        Example:
            config = Config.from_env()
        """
        return cls(
            model_id=_require("MODEL_ID"),
            temperature=float(os.environ.get("TEMPERATURE", 0)),
            max_tool_calls_per_run=int(os.environ.get("MAX_TOOL_CALLS_PER_RUN", 3)),
            prompts_file=os.environ.get("PROMPTS_FILE", "src/sonar/prompts/system.yaml"),
        )