"""Contract discovery agent implementation."""

import json
from pathlib import Path

from app.models.contract import ContractDiscoveryResult
from app.services.llm_driver.anthropic_handler import LLMClaude
from app.services.llm_driver.policies import AGENT, FILE_ACCESS_POLICY, TOOL

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
        self, codebase_path: str | Path, max_turns: int = 50, verbose: bool = True
    ) -> ContractDiscoveryResult:
        """Discover all contracts in a codebase.

        Args:
            codebase_path: Path to the codebase to analyze (e.g., "merit-travelops-demo/app")
            max_turns: Maximum number of turns for the agent (default: 100)

        Returns:
            ContractDiscoveryResult with all discovered contracts
        """
        codebase_path = Path(codebase_path).resolve()
        
        if not codebase_path.exists():
            raise ValueError(f"Codebase path does not exist: {codebase_path}")

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
        
        # Convert the text response to structured format
        if verbose:
            print(f"\n🔄 Converting response to structured format...")
            print(f"\n📄 Agent's text output (first 1000 chars):")
            print(response_text[:1000] if response_text else "None")
            print("...\n")
        
        result, _usage = await self.llm_client.create_object(
            model=self.llm_client.default_small_model,  # Use fast Haiku model for conversion
            prompt=f"""Convert the agent's contract analysis into a structured ContractDiscoveryResult.

Codebase: {codebase_path}

Agent's Report:
{response_text}

Your Task:
1. Parse each CONTRACT section into a ContractObligation object
2. Parse each OBLIGATION subsection into an ObligationRule within its parent contract
3. Populate all required fields properly

ContractObligation Required Fields:
- id: Like "contract.api-response.v1"
- version: "1.0.0"
- name: Optional display name
- task_context: TaskContext(goal="...", inputs={{}}, constraints=[])
- output_contract: OutputContract(format="json"|"markdown"|"text"|"code_patch", schema_definition={{}}, required_fields=[])
- obligations: list[ObligationRule] - at least 1
- acceptance_policy: AcceptancePolicy(require_all_hard_obligations=true, block_on=["critical"])

ObligationRule Required Fields:
- id: Like "OBL-001"
- description: What this rule checks
- applies_to: ["all"] or ["final_response"] etc.
- rule: Machine-readable condition
- validator: "jsonschema" | "deterministic_check" | "test_command" | "rubric" | "manual"
- enforcement: "hard" | "soft" (default: "hard")
- severity: "critical" | "major" | "minor" (default: "major")

CRITICAL Requirements:
- codebase_path: "{codebase_path}"
- total_contracts: Count of ContractObligation objects
- contracts: Array of ContractObligation objects (8-12 contracts)
- summary: High-level overview

Return a complete, valid ContractDiscoveryResult.""",
            schema=self.output_type,
        )
        
        return result
