"""Main script to run contract discovery on a codebase."""

import asyncio
import json
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from app.models.contract import ContractDiscoveryResult
from app.services.contract_discovery import ContractDiscoveryAgent
from app.services.llm_driver.anthropic_handler import LLMClaude

# Load environment variables
load_dotenv()


async def run_contract_discovery(
    codebase_path: str, output_file: str | None = None, max_turns: int = 100
) -> ContractDiscoveryResult:
    """Run contract discovery on a codebase.

    Args:
        codebase_path: Path to codebase to analyze (e.g., "merit-travelops-demo/app")
        output_file: Optional path to save results as JSON
        max_turns: Maximum turns for agent (default: 100)

    Returns:
        ContractDiscoveryResult with all discovered contracts
    """
    print(f"🔍 Starting contract discovery for: {codebase_path}")
    print(f"📊 Max turns: {max_turns}")
    print()

    # Initialize LLM client
    anthropic_client = AsyncAnthropic()
    llm_client = LLMClaude(anthropic_client)

    # Create and run agent
    agent = ContractDiscoveryAgent(llm_client)
    result = await agent.discover_contracts(codebase_path, max_turns=max_turns)

    # Print summary
    print("\n" + "=" * 80)
    print("📋 DISCOVERY COMPLETE")
    print("=" * 80)
    print(f"\n✅ Total contracts found: {result.total_contracts}")
    print(f"\n📁 Codebase: {result.codebase_path}")
    
    print("\n📊 By Type:")
    for contract_type, count in result.contracts_by_type.items():
        print(f"   - {contract_type}: {count}")
    
    print("\n🎯 By Severity:")
    for severity, count in result.contracts_by_severity.items():
        print(f"   - {severity}: {count}")
    
    print(f"\n📝 Summary:\n{result.summary}")

    # Print first few contracts as examples
    if result.contracts:
        print("\n" + "=" * 80)
        print("📖 SAMPLE CONTRACTS (first 3)")
        print("=" * 80)
        for i, contract in enumerate(result.contracts[:3], 1):
            print(f"\n{i}. {contract.title} ({contract.type.value})")
            print(f"   Severity: {contract.severity.value}")
            print(f"   Location: {contract.location.file_path}:{contract.location.line_start}-{contract.location.line_end}")
            print(f"   Description: {contract.description[:200]}...")

    # Save to file if requested
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("w") as f:
            json.dump(result.model_dump(), f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")

    return result


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Discover contracts in a Python codebase"
    )
    parser.add_argument(
        "codebase_path",
        help="Path to codebase to analyze (e.g., merit-travelops-demo/app)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to save results JSON file",
        default="contracts_output.json",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=100,
        help="Maximum turns for agent (default: 100)",
    )

    args = parser.parse_args()

    try:
        await run_contract_discovery(
            codebase_path=args.codebase_path,
            output_file=args.output,
            max_turns=args.max_turns,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
