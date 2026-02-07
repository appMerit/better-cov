"""Anthropic LLM handler for code analysis and structured outputs.

This module was migrated from merit-analyzer. Contains legacy code that
suppresses some linter rules for backwards compatibility.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast, get_type_hints

from anthropic import AsyncAnthropic, AsyncAnthropicBedrock, AsyncAnthropicVertex
from anthropic.types import ToolParam, ToolUseBlock
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    create_sdk_mcp_server,
    tool,
)
from dotenv import load_dotenv
from pydantic import BaseModel, create_model

from .abstract_provider_handler import LLMAbstractHandler, ModelT
from .policies import AGENT, FILE_ACCESS_POLICY, TOOL


load_dotenv()


def _deep_parse_json_strings(obj: Any) -> Any:
    """Recursively parse JSON strings in nested structures.

    Anthropic's tool calling API sometimes returns nested fields as JSON strings
    instead of fully parsed objects. This function recursively parses those strings.

    Args:
        obj: The object to parse (dict, list, or primitive)

    Returns:
        The object with all JSON strings parsed into Python objects
    """
    if isinstance(obj, dict):
        return {key: _deep_parse_json_strings(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_deep_parse_json_strings(item) for item in obj]
    if isinstance(obj, str):
        # Try to parse as JSON if it looks like JSON
        stripped = obj.strip()
        if (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        ):
            try:
                parsed = json.loads(obj)
                # Recursively parse the parsed object in case it has nested JSON strings
                return _deep_parse_json_strings(parsed)
            except (json.JSONDecodeError, ValueError):
                # Not valid JSON, return as-is
                return obj
        return obj
    # Primitives (int, float, bool, None) pass through unchanged
    return obj


class LLMClaude(LLMAbstractHandler):  # noqa: D101
    default_small_model = "claude-haiku-4-5"
    default_big_model = "claude-sonnet-4-5"
    standard_tools_map = {
        TOOL.READ: "Read",
        TOOL.WRITE: "Write",
        TOOL.EDIT: "Edit",
        TOOL.GREP: "Grep",
        TOOL.GLOB: "Glob",
        TOOL.BASH: "Bash",
        TOOL.WEB_FETCH: "WebFetch",
        TOOL.WEB_SEARCH: "WebSearch",
        TOOL.TODO_WRITE: "TodoWrite",
        TOOL.BASH_OUTPUT: "BashOutput",
        TOOL.KILL_BASH: "KillBash",
        TOOL.LIST_MCP_RESOURCES: "ListMcpResources",
        TOOL.READ_MCP_RESOURCE: "ReadMcpResource",
        TOOL.LS: "LS",
        TOOL.TASK: "Task",
        TOOL.SLASH_COMMAND: "SlashCommand",
    }
    file_access_map = {
        FILE_ACCESS_POLICY.READ_ONLY: "default",
        FILE_ACCESS_POLICY.READ_AND_WRITE: "acceptEdits",
        FILE_ACCESS_POLICY.FULL_ACCESS: "bypassPermissions",
        FILE_ACCESS_POLICY.READ_AND_PLAN: "plan",
    }

    def __init__(
        self, client: AsyncAnthropic | AsyncAnthropicBedrock | AsyncAnthropicVertex
    ):
        self.client = client
        self.compiled_agents: dict[AGENT, ClaudeAgentOptions] = {}

    async def create_object(
        self, prompt: str, schema: type[ModelT], model: str | None = None, max_retries: int = 2
    ) -> tuple[ModelT, dict[str, int]]:
        """Create an object from LLM response with retry logic.

        Returns:
            Tuple of (parsed_object, usage_dict) where usage_dict contains:
                - total_tokens: Total tokens used
                - prompt_tokens: Input tokens
                - completion_tokens: Output tokens
        """
        client = self.client
        tools: list[ToolParam] = [
            {
                "name": "emit_structured_result",
                "description": (
                    "Emit the structured result. ALL required fields must be provided. "
                    "Follow the schema exactly - do not omit required fields."
                ),
                "input_schema": schema.model_json_schema(),
            }
        ]
        
        last_error = None
        total_usage = {"total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0}
        
        for attempt in range(max_retries):
            try:
                msg = await client.messages.create(
                    model=model or self.default_big_model,
                    temperature=0,
                    max_tokens=16384,  # Increased for complex ContractObligation outputs
                    messages=[{"role": "user", "content": prompt}],
                    tools=tools,
                    tool_choice={"type": "tool", "name": "emit_structured_result"},
                )
                
                # Accumulate usage
                total_usage["total_tokens"] += msg.usage.input_tokens + msg.usage.output_tokens
                total_usage["prompt_tokens"] += msg.usage.input_tokens
                total_usage["completion_tokens"] += msg.usage.output_tokens
                
                tool_call = next(b for b in msg.content if isinstance(b, ToolUseBlock))

                # Parse any nested JSON strings
                parsed_input = _deep_parse_json_strings(tool_call.input)

                # Fix: Sometimes Anthropic wraps response in "input_schema" key
                if (
                    isinstance(parsed_input, dict)
                    and "input_schema" in parsed_input
                    and len(parsed_input) == 1
                ):
                    parsed_input = parsed_input["input_schema"]

                # Auto-truncate long strings
                if 'summary' in parsed_input and isinstance(parsed_input['summary'], str):
                    if len(parsed_input['summary']) > 1000:
                        parsed_input['summary'] = parsed_input['summary'][:997] + "..."
                
                # Truncate long strings in nested objects
                if 'contracts' in parsed_input and isinstance(parsed_input['contracts'], list):
                    for contract in parsed_input['contracts']:
                        if isinstance(contract, dict):
                            for field in ['title', 'description', 'expected_behavior', 'test_strategy']:
                                if field in contract and isinstance(contract[field], str):
                                    max_len = {'title': 100, 'description': 500, 'expected_behavior': 300, 'test_strategy': 300}.get(field, 500)
                                    if len(contract[field]) > max_len:
                                        contract[field] = contract[field][:max_len-3] + "..."
                
                # Validate and return
                return schema.model_validate(parsed_input), total_usage
                
            except Exception as e:
                last_error = e
                print(f"⚠️  Validation attempt {attempt + 1} failed: {str(e)[:200]}")
                if attempt < max_retries - 1:
                    # Retry with more explicit prompt
                    prompt = f"""{prompt}

IMPORTANT: Your previous attempt failed with error: {str(e)}
Make sure to include ALL required fields in the schema, especially:
- contracts: must be an array of objects (not empty unless truly no contracts found)
- summary: must be a string describing findings
- All nested required fields must be populated
Check the schema carefully and provide complete data."""
                    continue
                else:
                    # Last attempt failed, add defaults
                    try:
                        parsed_input = {}
                        if hasattr(schema, 'model_fields'):
                            for field_name, field_info in schema.model_fields.items():
                                if field_info.is_required():
                                    if field_name == 'contracts':
                                        parsed_input[field_name] = []
                                    elif field_name == 'summary':
                                        parsed_input[field_name] = "Failed to extract complete results"
                                    elif field_name == 'codebase_path':
                                        parsed_input[field_name] = "."
                                    elif field_name == 'total_contracts':
                                        parsed_input[field_name] = 0
                        return schema.model_validate(parsed_input), total_usage
                    except:
                        raise last_error

    def compile_agent(  # noqa: D102
        self,
        agent_name: AGENT,
        system_prompt: str | None,
        model: str | None = None,
        file_access: FILE_ACCESS_POLICY = FILE_ACCESS_POLICY.READ_ONLY,
        standard_tools: list[TOOL] | None = None,
        extra_tools: list[Callable] | None = None,
        output_type: type[ModelT | str] = str,
        cwd: str | Path | None = None,
    ):
        standard_tools = standard_tools or []
        extra_tools = extra_tools or []
        agent_config = ClaudeAgentOptions(
            model=model or self.default_big_model,
            allowed_tools=[self.standard_tools_map[tool] for tool in standard_tools],
            permission_mode=self.file_access_map[file_access],  # type: ignore[arg-type]
            system_prompt=system_prompt,
            cwd=cwd,
        )

        parsed_tools = []

        for extra_tool in extra_tools:
            name = extra_tool.__name__
            description = extra_tool.__doc__ or ""
            input_schema = create_model(
                f"InputSchema{name}",
                **{n: (tp, ...) for n, tp in get_type_hints(extra_tool)},
            )  # type: ignore[arg-type]
            parsed_tool = tool(
                name=name, description=description, input_schema=input_schema
            )(extra_tool)
            parsed_tools.append(parsed_tool)
            agent_config.allowed_tools.append(f"mcp__extra_tools__{name}")

        if parsed_tools:
            agent_config.mcp_servers = {
                "extra_tools": create_sdk_mcp_server(
                    name="extra_tools", tools=parsed_tools
                )
            }

        self.compiled_agents[agent_name] = agent_config

    async def run_agent(  # noqa: D102
        self,
        agent: AGENT,
        task: str,
        output_type: type[ModelT | str] = str,
        max_turns: int | None = None,
        verbose: bool = True,
    ) -> ModelT | str:
        options = self.compiled_agents[agent]
        options.max_turns = max_turns
        client_response = None
        turn_count = 0
        last_assistant_message = None

        async with ClaudeSDKClient(options=options) as client:
            await client.query(task)
            async for message in client.receive_response():
                if verbose:
                    # Debug: show all message types
                    msg_type = type(message).__name__
                    
                match message:
                    case AssistantMessage():
                        turn_count += 1
                        last_assistant_message = message
                        if verbose:
                            print(f"🔄 Turn {turn_count}/{max_turns or '∞'}: Agent thinking...")
                        continue
                    case ResultMessage(result=res):
                        client_response = res
                        if verbose:
                            print(f"✅ Agent completed in {turn_count} turns")
                    case _:
                        # Log other message types to help debug
                        if verbose:
                            print(f"   📨 {msg_type}")
                        continue

        if not client_response:
            raise ValueError(
                f"Agent '{agent}' completed without returning a result. "
                "This usually means the agent didn't call emit_structured_result. "
                f"Turns completed: {turn_count}/{max_turns or 'unlimited'}. "
                "Check that the prompt instructs the agent to use emit_structured_result."
            )

        if isinstance(client_response, output_type):
            return cast("ModelT", client_response)

        if issubclass(output_type, BaseModel) and isinstance(client_response, str):
            prompt_template = f"""
                Your job is to transform the following text into a JSON and submit result
                using the 'emit_structured_result' tool. Be very careful with the JSON
                schema: read all field descriptions, check all required and optional types,
                and parse the data according to this schema.

                While parsing, you can rephrase / rewrite the original information to make it
                better align with the schema.

                <information_for_parsing>
                    {client_response}
                </information_for_parsing>

                <json_schema>
                    {output_type.model_json_schema()}
                </json_schema>
                """
            result, _usage = await self.create_object(
                model=self.default_small_model,
                schema=output_type,
                prompt=prompt_template,
            )
            return result

        msg = f"Client output can't be parsed as {output_type}"
        raise TypeError(msg)
