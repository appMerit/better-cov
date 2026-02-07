"""Configuration management for TravelOps Assistant."""

import os
from dataclasses import dataclass
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not required


@dataclass
class Config:
    """Application configuration."""

    llm_provider: str = "stub"  # "stub" or "openai"
    temperature: float = 0.0
    max_agent_steps: int = 5
    openai_api_key: str | None = None
    enable_retrieval: bool = True
    enable_memory: bool = True
    enable_routing: bool = True


def get_config() -> Config:
    """Get configuration from environment variables."""
    return Config(
        llm_provider=os.getenv("TRAVELOPS_LLM_PROVIDER", "stub").lower(),  # Normalize to lowercase
        temperature=float(os.getenv("TRAVELOPS_TEMPERATURE", "0.0")),
        max_agent_steps=int(os.getenv("TRAVELOPS_MAX_STEPS", "5")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        enable_retrieval=os.getenv("TRAVELOPS_ENABLE_RETRIEVAL", "true").lower() == "true",
        enable_memory=os.getenv("TRAVELOPS_ENABLE_MEMORY", "true").lower() == "true",
        enable_routing=os.getenv("TRAVELOPS_ENABLE_ROUTING", "true").lower() == "true",
    )
