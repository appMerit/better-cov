"""OpenAI LLM handler for code analysis and structured outputs.

This module was migrated from merit-analyzer. Contains legacy code that
suppresses some linter rules for backwards compatibility.
"""

from collections.abc import Callable
from pathlib import Path

from agents import Agent, Runner, function_tool
from dotenv import load_dotenv
from openai import AsyncOpenAI

from .abstract_provider_handler import LLMAbstractHandler, ModelT
from .defaults import MAX_AGENT_TURNS
from .local_tools import edit, glob, grep, ls, read, todo, write
from .policies import AGENT, FILE_ACCESS_POLICY, TOOL


load_dotenv()


class LLMOpenAI(LLMAbstractHandler):
    """Handler for OpenAI models through structured outputs API."""

    default_small_model = "gpt-5-mini"
    default_big_model = "gpt-5"
    default_embedding_model = "text-embedding-3-small"
    standard_tools_map = {
        TOOL.READ: read,
        TOOL.WRITE: write,
        TOOL.EDIT: edit,
        TOOL.GREP: grep,
        TOOL.GLOB: glob,
        TOOL.BASH: None,
        TOOL.WEB_FETCH: "WebFetch",
        TOOL.WEB_SEARCH: "WebSearch",
        TOOL.TODO_WRITE: todo,
        TOOL.BASH_OUTPUT: "BashOutput",
        TOOL.KILL_BASH: "KillBash",
        TOOL.LIST_MCP_RESOURCES: None,
        TOOL.READ_MCP_RESOURCE: None,
        TOOL.LS: ls,
        TOOL.TASK: None,
        TOOL.SLASH_COMMAND: None,
    }

    def __init__(self, open_ai_client: AsyncOpenAI):
        self.client = open_ai_client
        self.compiled_agents: dict[AGENT, Agent] = {}

    async def generate_embeddings(
        self, input_values: list[str], model: str | None = None
    ) -> list[list[float]]:  # noqa: D102
        response = await self.client.embeddings.create(
            model=model or self.default_embedding_model, input=input_values
        )
        return [item.embedding for item in response.data]

    async def create_object(
        self, prompt: str, schema: type[ModelT], model: str | None = None
    ) -> tuple[ModelT, dict[str, int]]:
        """Create an object from LLM response.

        Returns:
            Tuple of (parsed_object, usage_dict) where usage_dict contains:
                - total_tokens: Total tokens used
                - prompt_tokens: Input tokens
                - completion_tokens: Output tokens
        """
        model = model or self.default_big_model
        # Use OpenAI's structured outputs API for proper Pydantic parsing
        completion = await self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema,
        )

        message = completion.choices[0].message
        parsed = completion.choices[0].message.parsed
        if not parsed:
            # If parsing failed, try to show what we got
            if hasattr(message, "content"):
                print(f"❌ Parsing failed. Raw content: {message.content}")  # noqa: T201
            msg = "LLM didn't return any objects"
            raise ValueError(msg)

        # Extract usage information
        usage = {}
        if completion.usage:
            usage = {
                "total_tokens": completion.usage.total_tokens or 0,
                "prompt_tokens": completion.usage.prompt_tokens or 0,
                "completion_tokens": completion.usage.completion_tokens or 0,
            }
        else:
            usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}

        return parsed, usage

    def compile_agent(  # noqa: D102
        self,
        agent_name: AGENT,
        system_prompt: str | None,
        model: str | None = None,
        file_access: FILE_ACCESS_POLICY = FILE_ACCESS_POLICY.READ_ONLY,
        standard_tools: list[TOOL] | None = None,
        extra_tools: list[Callable] | None = None,
        cwd: str | Path | None = None,
        output_type: type[ModelT | str] = str,
    ):
        standard_tools = standard_tools or []
        extra_tools = extra_tools or []
        tools = []
        for standard_tool in standard_tools:
            if standard_tool not in file_access.value:
                msg = (
                    f"Tool {standard_tool.name} doesn't comply with access policy {file_access.name}. "
                    "Change file access policy, or remove the tool from the given tools."
                )
                raise ValueError(msg)
            if standard_tool.value is None:
                msg = (
                    f"Tool {standard_tool.name} has not been implemented for the OpenAI client yet. "
                    "Remove the tool from given arguments, or implement it for the OpenAI handler."
                )
                raise ValueError(msg)
            parsed_tool = self.standard_tools_map[standard_tool]
            tools.append(function_tool(parsed_tool))

        tools.extend(function_tool(extra_tool) for extra_tool in extra_tools)

        agent = Agent(
            name=agent_name.value,
            instructions=system_prompt,
            model=model or self.default_big_model,
            tools=tools,
            output_type=output_type,
        )
        self.compiled_agents[agent_name] = agent

    async def run_agent(  # noqa: D102
        self,
        agent: AGENT,
        task: str,
        output_type: type[ModelT | str],
        max_turns: int | None = None,
    ) -> ModelT | str:
        compiled = self.compiled_agents[agent]
        result = await Runner.run(
            compiled, input=task, max_turns=max_turns or MAX_AGENT_TURNS
        )
        return result.final_output_as(output_type)
