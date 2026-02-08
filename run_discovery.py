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
    callable_ref: str,
    output_file: str | None = None,
    max_turns: int = 50,
    verbose: bool = True,
    debug: bool = False,
) -> ContractDiscoveryResult:
    """Run contract discovery rooted at a Python callable entrypoint.

    Args:
        callable_ref: Callable reference string in the form "{file.py}:{qualname}"
        output_file: Optional path to save results as JSON
        max_turns: Maximum turns for agent (default: 50)

    Returns:
        ContractDiscoveryResult with all discovered contracts
    """
    print(f"🔍 Starting contract discovery for: {callable_ref}")
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
        callable_ref, max_turns=max_turns, verbose=verbose
    )

    # Print summary
    print("\n" + "=" * 80)
    print("📋 DISCOVERY COMPLETE")
    print("=" * 80)
    total_contracts = len(result.contracts)
    print(f"\n✅ Total contracts found: {total_contracts}")
    
    # Count obligations by enforcement and severity (validator is encoded inside `rule`)
    if result.contracts:
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
        
        print(f"\n📋 Total Obligations: {total_obligations}")
        
        print("\n⚖️  By Enforcement:")
        for enforcement, count in sorted(enforcement_counts.items()):
            print(f"   - {enforcement}: {count}")
        
        print("\n🎯 By Severity:")
        for severity, count in sorted(severity_counts.items()):
            print(f"   - {severity}: {count}")

    # Print first few contracts as examples
    if result.contracts:
        print("\n" + "=" * 80)
        print("📖 SAMPLE CONTRACTS (first 2)")
        print("=" * 80)
        for i, contract in enumerate(result.contracts[:2], 1):
            print(f"\n{i}. {contract.name}")
            print(f"   Obligations: {len(contract.obligations)}")
            for j, obl in enumerate(contract.obligations[:3], 1):
                print(f"      {j}. {obl.id}: {obl.description[:70]}...")
                print(f"         Location: {obl.location}")
                print(f"         Enforcement: {obl.enforcement}, Severity: {obl.severity}")
                print(f"         Rule: {obl.rule[:120]}...")

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
        description="Discover contracts in a Python codebase rooted at a callable entrypoint"
    )
    parser.add_argument(
        "callable_ref",
        help='Callable reference string "{file.py}:{qualname}" (e.g., merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__)',
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
            callable_ref=args.callable_ref,
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
