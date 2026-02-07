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
    codebase_path: str, output_file: str | None = None, max_turns: int = 50, verbose: bool = True, debug: bool = False
) -> ContractDiscoveryResult:
    """Run contract discovery on a codebase.

    Args:
        codebase_path: Path to codebase to analyze (e.g., "merit-travelops-demo/app")
        output_file: Optional path to save results as JSON
        max_turns: Maximum turns for agent (default: 50)

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
    
    if verbose:
        print("🤖 Agent starting analysis...")
        print()
    
    result = await agent.discover_contracts(
        codebase_path, max_turns=max_turns, verbose=verbose
    )

    # Print summary
    print("\n" + "=" * 80)
    print("📋 DISCOVERY COMPLETE")
    print("=" * 80)
    print(f"\n✅ Total contracts found: {result.total_contracts}")
    print(f"\n📁 Codebase: {result.codebase_path}")
    
    # Count obligations by validator, enforcement, and severity
    if result.contracts:
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
        
        print(f"\n📋 Total Obligations: {total_obligations}")
        
        print("\n🔍 By Validator Type:")
        for validator, count in sorted(validator_counts.items()):
            print(f"   - {validator}: {count}")
        
        print("\n⚖️  By Enforcement:")
        for enforcement, count in enforcement_counts.items():
            print(f"   - {enforcement}: {count}")
        
        print("\n🎯 By Severity:")
        for severity, count in sorted(severity_counts.items()):
            print(f"   - {severity}: {count}")
    
    print(f"\n📝 Summary:\n{result.summary}")

    # Print first few contracts as examples
    if result.contracts:
        print("\n" + "=" * 80)
        print("📖 SAMPLE CONTRACTS (first 2)")
        print("=" * 80)
        for i, contract in enumerate(result.contracts[:2], 1):
            print(f"\n{i}. {contract.name or contract.id} (v{contract.version})")
            print(f"   ID: {contract.id}")
            print(f"   Goal: {contract.task_context.goal}")
            print(f"   Output Format: {contract.output_contract.format}")
            print(f"   Obligations: {len(contract.obligations)}")
            for j, obl in enumerate(contract.obligations[:3], 1):
                print(f"      {j}. {obl.id}: {obl.description[:70]}...")
                print(f"         Validator: {obl.validator}, Enforcement: {obl.enforcement}, Severity: {obl.severity}")

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
        default=50,
        help="Maximum turns for agent (default: 50)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress logging",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed debug information",
    )

    args = parser.parse_args()

    try:
        # Enable debug logging if requested
        if args.debug:
            import logging
            logging.basicConfig(level=logging.DEBUG)
        
        await run_contract_discovery(
            codebase_path=args.codebase_path,
            output_file=args.output,
            max_turns=args.max_turns,
            verbose=not args.quiet,
            debug=args.debug,
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
