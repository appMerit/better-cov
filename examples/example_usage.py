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
        max_turns=100
    )
    
    # Print results
    print(f"\nFound {result.total_contracts} contracts!")
    print(f"\nSummary: {result.summary}")
    
    # Print all hard contracts (format-based)
    hard_contract_types = ["json_schema", "type_hint", "api_contract", "data_format", "validation_rule"]
    hard_contracts = [c for c in result.contracts if c.type.value in hard_contract_types]
    
    print(f"\n{'='*80}")
    print(f"HARD CONTRACTS ({len(hard_contracts)})")
    print('='*80)
    
    for contract in hard_contracts:
        print(f"\n📋 {contract.title}")
        print(f"   Type: {contract.type.value} | Severity: {contract.severity.value}")
        print(f"   Location: {contract.location.file_path}:{contract.location.line_start}")
        print(f"   {contract.description[:150]}...")
    
    # Print all soft contracts (behavioral)
    soft_contract_types = ["behavioral", "policy", "constraint", "guideline"]
    soft_contracts = [c for c in result.contracts if c.type.value in soft_contract_types]
    
    print(f"\n{'='*80}")
    print(f"SOFT CONTRACTS ({len(soft_contracts)})")
    print('='*80)
    
    for contract in soft_contracts:
        print(f"\n💭 {contract.title}")
        print(f"   Type: {contract.type.value} | Severity: {contract.severity.value}")
        print(f"   Location: {contract.location.file_path}:{contract.location.line_start}")
        print(f"   {contract.description[:150]}...")
    
    # Show contracts by component
    print(f"\n{'='*80}")
    print("CONTRACTS BY COMPONENT")
    print('='*80)
    
    # Group contracts by affected components
    component_contracts = {}
    for contract in result.contracts:
        for component in contract.affected_components:
            if component not in component_contracts:
                component_contracts[component] = []
            component_contracts[component].append(contract)
    
    for component, contracts in sorted(component_contracts.items()):
        print(f"\n{component}: {len(contracts)} contracts")
        for contract in contracts[:3]:  # Show first 3
            print(f"  - {contract.title} ({contract.type.value})")
    
    # Testable vs non-testable
    testable = [c for c in result.contracts if c.testable]
    non_testable = [c for c in result.contracts if not c.testable]
    
    print(f"\n{'='*80}")
    print(f"TESTABILITY")
    print('='*80)
    print(f"Testable: {len(testable)}")
    print(f"Non-testable: {len(non_testable)}")
    
    # Show some test strategies
    print("\nExample test strategies:")
    for contract in testable[:5]:
        print(f"\n  {contract.title}:")
        print(f"    {contract.test_strategy}")


if __name__ == "__main__":
    asyncio.run(main())
