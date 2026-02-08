"""Example: Using the Contract Discovery Agent programmatically."""

import asyncio

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
    
    # Run discovery rooted at a specific callable (file.py:qualname)
    callable_ref = "merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__"
    
    print(f"Analyzing entry callable: {callable_ref}")
    
    result = await agent.discover_contracts(
        callable_ref=callable_ref,
        max_turns=50
    )
    
    # Count obligations by enforcement and severity (validator is encoded in `rule`)
    enforcement_counts: dict[str, int] = {"hard": 0, "soft": 0}
    severity_counts: dict[str, int] = {}
    total_obligations = 0
    
    for contract in result.contracts:
        for obligation in contract.obligations:
            total_obligations += 1
            enforcement_counts[str(obligation.enforcement)] = (
                enforcement_counts.get(str(obligation.enforcement), 0) + 1
            )
            severity_counts[str(obligation.severity)] = (
                severity_counts.get(str(obligation.severity), 0) + 1
            )
    
    print(f"\n{'='*80}")
    print(f"OBLIGATION STATISTICS")
    print('='*80)
    print(f"Total Obligations: {total_obligations}")
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
        print(f"\n{i}. {contract.name}")
        print(f"   Obligations: {len(contract.obligations)}")
        
        for j, obl in enumerate(contract.obligations[:3], 1):
            print(f"\n      {j}. {obl.id}: {obl.description}")
            print(f"         Location: {obl.location}")
            print(f"         Enforcement: {obl.enforcement}")
            print(f"         Severity: {obl.severity}")
            print(f"         Rule: {obl.rule[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
