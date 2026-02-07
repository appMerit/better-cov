"""Example: Using the Contract Discovery Agent programmatically."""

import asyncio
from pathlib import Path

from anthropic import AsyncAnthropic

from app.services.contract_discovery import ContractDiscoveryAgent
from app.services.llm_driver.anthropic_handler import LLMClaude


async def main():
    """Example usage of the contract discovery agent."""
    
    # Initialize the Anthropic client
    anthropic_client = AsyncAnthropic()
    
    # Create the LLM client wrapper
    llm_client = LLMClaude(anthropic_client)
    
    # Create the contract discovery agent
    agent = ContractDiscoveryAgent(llm_client)
    
    # Run discovery on the merit-travelops-demo codebase
    codebase_path = Path("merit-travelops-demo/app")
    
    print(f"Analyzing codebase: {codebase_path}")
    
    result = await agent.discover_contracts(
        codebase_path=codebase_path,
        max_turns=50
    )
    
    # Print results
    print(f"\nFound {result.total_contracts} contracts!")
    print(f"\nSummary: {result.summary}")
    
    # Count obligations by validator type
    validator_counts = {}
    enforcement_counts = {"hard": 0, "soft": 0}
    severity_counts = {}
    total_obligations = 0
    
    for contract in result.contracts:
        for obligation in contract.obligations:
            total_obligations += 1
            validator_counts[obligation.validator] = validator_counts.get(obligation.validator, 0) + 1
            enforcement_counts[obligation.enforcement] += 1
            severity_counts[obligation.severity] = severity_counts.get(obligation.severity, 0) + 1
    
    print(f"\n{'='*80}")
    print(f"OBLIGATION STATISTICS")
    print('='*80)
    print(f"Total Obligations: {total_obligations}")
    print(f"\nBy Validator:")
    for validator, count in sorted(validator_counts.items()):
        print(f"  - {validator}: {count}")
    print(f"\nBy Enforcement:")
    for enforcement, count in enforcement_counts.items():
        print(f"  - {enforcement}: {count}")
    print(f"\nBy Severity:")
    for severity, count in sorted(severity_counts.items()):
        print(f"  - {severity}: {count}")
    
    # Print sample contracts
    print(f"\n{'='*80}")
    print(f"SAMPLE CONTRACTS (first 3)")
    print('='*80)
    
    for i, contract in enumerate(result.contracts[:3], 1):
        print(f"\n{i}. {contract.name or contract.id} (v{contract.version})")
        print(f"   ID: {contract.id}")
        print(f"   Goal: {contract.task_context.goal}")
        print(f"   Output Format: {contract.output_contract.format}")
        print(f"   Target Agents: {', '.join(contract.target_agents)}")
        print(f"   Obligations: {len(contract.obligations)}")
        
        for j, obl in enumerate(contract.obligations[:3], 1):
            print(f"\n      {j}. {obl.id}: {obl.description}")
            print(f"         Validator: {obl.validator}")
            print(f"         Enforcement: {obl.enforcement}")
            print(f"         Severity: {obl.severity}")
            print(f"         Rule: {obl.rule[:100]}...")
            if obl.code_location:
                print(f"         Location: {obl.code_location}")
    
    # Show acceptance policies
    print(f"\n{'='*80}")
    print(f"ACCEPTANCE POLICIES")
    print('='*80)
    
    for contract in result.contracts[:3]:
        policy = contract.acceptance_policy
        print(f"\n{contract.name or contract.id}:")
        print(f"  - Require all hard obligations: {policy.require_all_hard_obligations}")
        print(f"  - Block on severities: {', '.join(policy.block_on)}")
        print(f"  - Use weighted scoring: {policy.use_weighted_scoring}")
        if policy.use_weighted_scoring:
            print(f"  - Min weighted score: {policy.min_weighted_score}")


if __name__ == "__main__":
    asyncio.run(main())
