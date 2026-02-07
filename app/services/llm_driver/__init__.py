"""Handle LLM clients."""

import asyncio
import os

from dotenv import load_dotenv
from pydantic import BaseModel

from .abstract_provider_handler import LLMAbstractHandler
from .anthropic_handler import LLMClaude
from .openai_handler import LLMOpenAI
from .policies import AGENT, FILE_ACCESS_POLICY, TOOL


load_dotenv()

cached_client: LLMAbstractHandler | None = None
cached_key: tuple[str, str] | None = None
client_lock = asyncio.Lock()
validated_once = False

SUPPORTED = {
    "openai": ["openai"],
    "anthropic": ["anthropic", "gcp", "aws"],
}


async def build_llm_client(
    model_vendor: str, inference_vendor: str
) -> LLMAbstractHandler:
    """Get the right LLM client based on model and vendor."""
    mv = model_vendor.lower().strip()
    ip = inference_vendor.lower().strip()

    if not mv:
        raise ValueError("MODEL_VENDOR has not been provided in ENV.")
    if not ip:
        raise ValueError("INFERENCE_VENDOR has not been provided in ENV.")

    match mv, ip:
        case "openai", "openai":
            from openai import AsyncOpenAI

            client = LLMOpenAI(AsyncOpenAI())

        case "anthropic", "aws":
            os.environ["CLAUDE_CODE_USE_BEDROCK"] = "1"
            from anthropic import AsyncAnthropicBedrock

            client = LLMClaude(AsyncAnthropicBedrock())
            client.default_big_model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
            client.default_small_model = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

        case "anthropic", "gcp":
            os.environ["CLAUDE_CODE_USE_VERTEX"] = "1"
            from anthropic import AsyncAnthropicVertex

            region = os.getenv("CLOUD_ML_REGION", "us-east5")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv(
                "ANTHROPIC_VERTEX_PROJECT_ID"
            )
            if not project_id:
                raise ValueError(
                    "GOOGLE_CLOUD_PROJECT or ANTHROPIC_VERTEX_PROJECT_ID must be set for Vertex AI"
                )

            client = LLMClaude(
                AsyncAnthropicVertex(region=region, project_id=project_id)
            )
            client.default_big_model = "claude-sonnet-4-5@20250929"
            client.default_small_model = "claude-haiku-4-5@20251001"

        case "anthropic", "anthropic":
            from anthropic import AsyncAnthropic

            client = LLMClaude(AsyncAnthropic())

        case _, _:
            if mv not in SUPPORTED:
                raise ValueError(
                    f"{mv} is not supported yet. Available model families: {list(SUPPORTED.keys())}"
                )
            if ip not in SUPPORTED[mv]:
                raise ValueError(
                    f"{ip} is not supported for {mv}. Supported providers for {mv}: {SUPPORTED[mv]}"
                )

    return client


async def validate_client(client: LLMAbstractHandler) -> None:
    """Health check."""

    class TestSchema(BaseModel):
        response: str

    _result, _usage = await client.create_object(
        prompt='Return JSON: {"response": "True"}',
        schema=TestSchema,
    )


async def get_llm_client() -> LLMAbstractHandler:
    """Return a cached LLM client built from MODEL_VENDOR and INFERENCE_VENDOR.
    Rebuilds if envs changed.
    """
    global cached_client, cached_key, validated_once

    model_vendor = os.getenv("MODEL_VENDOR") or ""
    inference_vendor = os.getenv("INFERENCE_VENDOR") or ""
    key = (model_vendor.lower().strip(), inference_vendor.lower().strip())

    if cached_client is not None and cached_key == key:
        return cached_client

    async with client_lock:
        if cached_client is not None and cached_key == key:  # yes async is cursed
            return cached_client

        client = await build_llm_client(*key)

        if not validated_once:
            await validate_client(client)
            validated_once = True

        cached_client = client
        cached_key = key
        return cached_client


cached_data_gen_client: LLMAbstractHandler | None = None
cached_data_gen_key: tuple[str, str, str] | None = None
data_gen_client_lock = asyncio.Lock()
data_gen_validated_once = False


async def get_data_gen_llm_client() -> LLMAbstractHandler:
    """Return a cached LLM client specifically for data generation.

    Uses separate env vars:
    - DATA_GEN_MODEL_VENDOR (default: same as MODEL_VENDOR)
    - DATA_GEN_INFERENCE_VENDOR (default: same as INFERENCE_VENDOR)
    - DATA_GEN_MODEL (optional: specific model override like 'gpt-4o-mini')

    Falls back to regular LLM client if DATA_GEN_* vars not set.
    """
    global cached_data_gen_client, cached_data_gen_key, data_gen_validated_once

    # Check for data-gen specific config
    model_vendor = os.getenv("DATA_GEN_MODEL_VENDOR") or os.getenv("MODEL_VENDOR") or ""
    inference_vendor = (
        os.getenv("DATA_GEN_INFERENCE_VENDOR") or os.getenv("INFERENCE_VENDOR") or ""
    )
    specific_model = os.getenv("DATA_GEN_MODEL") or ""  # e.g., "gpt-4o-mini"

    key = (
        model_vendor.lower().strip(),
        inference_vendor.lower().strip(),
        specific_model.lower().strip(),
    )

    if cached_data_gen_client is not None and cached_data_gen_key == key:
        return cached_data_gen_client

    async with data_gen_client_lock:
        if cached_data_gen_client is not None and cached_data_gen_key == key:
            return cached_data_gen_client

        client = await build_llm_client(model_vendor, inference_vendor)

        # Override model if specific model requested
        if specific_model:
            if hasattr(client, "default_big_model"):
                client.default_big_model = specific_model
            if hasattr(client, "model"):
                client.model = specific_model

        if not data_gen_validated_once:
            await validate_client(client)
            data_gen_validated_once = True

        cached_data_gen_client = client
        cached_data_gen_key = key
        return cached_data_gen_client


__all__ = [
    "AGENT",
    "FILE_ACCESS_POLICY",
    "TOOL",
    "LLMAbstractHandler",
    "get_data_gen_llm_client",
    "get_llm_client",
]
