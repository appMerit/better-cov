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

        # Prepare task prompt
        schema = json.dumps(ContractDiscoveryResult.model_json_schema(), indent=2)
        task = TASK_TEMPLATE.format(
            codebase_path=str(codebase_path),
            schema=schema,
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
        
        result, _usage = await self.llm_client.create_object(
            prompt=f"""Based on the agent's contract analysis, create a complete ContractDiscoveryResult.

Agent's Analysis:
{response_text}

CRITICAL: You MUST populate ALL required fields:
- codebase_path: "{codebase_path}"
- total_contracts: Count of contracts found
- contracts: Array of Contract objects (extract each contract the agent found)
- summary: Brief summary of findings

Parse the agent's analysis carefully and extract every contract mentioned into the contracts array.
Each contract needs: id, type, severity, title, description, location (file_path, line_start, line_end, code_snippet), expected_behavior, test_strategy.

Return a complete ContractDiscoveryResult with the contracts array fully populated.""",
            schema=self.output_type,
        )
        
        return result
