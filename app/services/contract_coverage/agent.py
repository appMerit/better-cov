"""Contract coverage agent implementation."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.contract import ContractCoverageResult, ContractDiscoveryResult
from app.services.contract_discovery.ast_analyzer import format_sut_ast, parse_callable
from app.services.llm_driver.anthropic_handler import LLMClaude
from app.services.llm_driver.policies import AGENT, FILE_ACCESS_POLICY, TOOL

from .prompts import SYSTEM_PROMPT, TASK_TEMPLATE


class ContractCoverageAgent:
    """Agent that finds obligations not covered by tests."""

    name = AGENT.CONTRACT_COVERAGE
    file_access = FILE_ACCESS_POLICY.READ_ONLY
    system_prompt = SYSTEM_PROMPT
    output_type = ContractCoverageResult
    standard_tools = [TOOL.GLOB, TOOL.GREP, TOOL.LS, TOOL.READ]

    def __init__(self, llm_client: LLMClaude):
        """Initialize the agent.

        Args:
            llm_client: Configured LLM client for Claude
        """
        self.llm_client = llm_client

    async def analyze_coverage(
        self,
        callable_ref: str,
        max_turns: int = 50,
        verbose: bool = True,
    ) -> ContractCoverageResult:
        """Analyze test coverage for obligations rooted at a callable.

        Args:
            callable_ref: Callable reference string in the form "{file.py}:{qualname}".
            max_turns: Maximum number of turns for the agent (default: 50)
            verbose: Whether to print progress messages

        Returns:
            ContractCoverageResult with uncovered obligation IDs
        """
        parsed = parse_callable(callable_ref)
        codebase_path = Path(parsed["sut_root"]).resolve()
        sut_ast_context = format_sut_ast(parsed)

        # Load obligations from results/contracts.json at repo root.
        repo_root = Path(__file__).resolve().parents[3]
        contracts_path = repo_root / "results" / "contracts.json"
        contracts_data = json.loads(contracts_path.read_text(encoding="utf-8"))
        contracts = ContractDiscoveryResult.model_validate(contracts_data)

        # Compile agent if not already compiled
        if self.name not in self.llm_client.compiled_agents:
            self.llm_client.compile_agent(
                agent_name=self.name,
                file_access=self.file_access,
                output_type=str,  # Let agent return string, we'll convert it
                standard_tools=self.standard_tools,
                system_prompt=self.system_prompt,
                cwd=codebase_path,
            )

        schema_json = json.dumps(ContractCoverageResult.model_json_schema(), indent=2)
        obligations_json = json.dumps(contracts.model_dump(), indent=2, default=str)
        task = TASK_TEMPLATE.format(
            codebase_path=str(codebase_path),
            callable_ref=callable_ref,
            sut_ast_context=sut_ast_context,
            obligations_json=f"```json\n{obligations_json}\n```",
            schema=f"```json\n{schema_json}\n```",
        )

        response_text = await self.llm_client.run_agent(
            agent=self.name,
            task=task,
            output_type=str,
            max_turns=max_turns,
            verbose=verbose,
        )

        if response_text:
            try:
                parsed_response = json.loads(response_text)
                return ContractCoverageResult.model_validate(parsed_response)
            except Exception:
                pass

        result, _usage = await self.llm_client.create_object(
            model=self.llm_client.default_small_model,
            prompt=f"""Convert the agent's coverage analysis into a structured ContractCoverageResult.

Codebase: {codebase_path}
Entry callable: {callable_ref}

Contract obligations:
{obligations_json}

Agent's Report:
{response_text}

Your Task:
1. Return the obligation IDs that are NOT covered by the tests.
2. Include only IDs that appear in the provided obligations.
3. If no uncovered obligations are found, return an empty list.

Return a complete, valid ContractCoverageResult JSON object. Do NOT add extra top-level fields.""",
            schema=self.output_type,
        )

        return result
