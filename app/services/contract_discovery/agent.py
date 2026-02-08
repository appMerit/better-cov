"""Contract discovery agent implementation."""

import json
from pathlib import Path

from app.models.contract import ContractDiscoveryResult
from app.services.llm_driver.anthropic_handler import LLMClaude
from app.services.llm_driver.policies import AGENT, FILE_ACCESS_POLICY, TOOL

from .ast_analyzer import format_sut_ast, parse_callable
from .prompts import SYSTEM_PROMPT, TASK_TEMPLATE


class ContractDiscoveryAgent:
    """Agent that discovers contracts in a codebase using Claude Code Agent SDK."""

    name = AGENT.CONTRACT_DISCOVERY
    file_access = FILE_ACCESS_POLICY.READ_ONLY
    system_prompt = SYSTEM_PROMPT
    output_type = ContractDiscoveryResult
    standard_tools = [TOOL.GLOB, TOOL.GREP, TOOL.LS, TOOL.READ]

    def __init__(self, llm_client: LLMClaude):
        """Initialize the agent.
        
        Args:
            llm_client: Configured LLM client for Claude
        """
        self.llm_client = llm_client

    async def discover_contracts(
        self, callable_ref: str, max_turns: int = 50, verbose: bool = True
    ) -> ContractDiscoveryResult:
        """Discover contract obligations for a Python system rooted at a callable.

        Args:
            callable_ref: Callable reference string in the form "{file.py}:{qualname}".
                Examples:
                  - "merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__"
                  - "app/main.py:main"
            max_turns: Maximum number of turns for the agent (default: 100)

        Returns:
            ContractDiscoveryResult with all discovered contracts
        """
        parsed = parse_callable(callable_ref)
        codebase_path = Path(parsed["sut_root"]).resolve()
        sut_ast_context = format_sut_ast(parsed)
        print(sut_ast_context)

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

        # Prepare task prompt with schema
        schema_json = json.dumps(ContractDiscoveryResult.model_json_schema(), indent=2)
        task = TASK_TEMPLATE.format(
            codebase_path=str(codebase_path),
            callable_ref=callable_ref,
            sut_ast_context=sut_ast_context,
            schema=f"```json\n{schema_json}\n```",
        )

        # Run agent - it will return a string description
        response_text = await self.llm_client.run_agent(
            agent=self.name,
            task=task,
            output_type=str,
            max_turns=max_turns,
            verbose=verbose,
        )
        
        # Fast-path: if the agent followed instructions and returned valid JSON,
        # validate it directly without a second LLM call.
        if response_text:
            try:
                parsed = json.loads(response_text)
                return ContractDiscoveryResult.model_validate(parsed)
            except Exception:
                # Fall back to conversion step below.
                pass

        # Convert the text response to structured format (LLM-powered parser)
        if verbose:
            print(f"\n🔄 Converting response to structured format...")
            print(f"\n📄 Agent's text output (first 1000 chars):")
            print(response_text[:1000] if response_text else "None")
            print("...\n")
        
        result, _usage = await self.llm_client.create_object(
            model=self.llm_client.default_small_model,  # Use fast Haiku model for conversion
            prompt=f"""Convert the agent's contract analysis into a structured ContractDiscoveryResult.

Codebase: {codebase_path}
Entry callable: {callable_ref}

Agent's Report:
{response_text}

Your Task:
1. Produce a `contracts` array with 8-12 ContractObligation objects when possible.
2. Each ContractObligation must have:
   - name: string
   - obligations: non-empty array of ObligationRule objects
3. Each ObligationRule must have:
   - id: string
   - location: string like "path/to/file.py:12-38"
   - description: string
   - rule: string (include how to validate inside the rule, e.g. "jsonschema: ...", "test_command: ...")
   - enforcement: "hard" | "soft"
   - severity: "critical" | "major" | "minor"

Return a complete, valid ContractDiscoveryResult JSON object. Do NOT add extra top-level fields.""",
            schema=self.output_type,
        )
        
        return result
