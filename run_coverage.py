"""Main script to run contract coverage analysis on a codebase."""

import asyncio
import json
from pathlib import Path

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

from app.models.contract import ContractCoverageResult
from app.services.contract_coverage import ContractCoverageAgent
from app.services.llm_driver.anthropic_handler import LLMClaude

# Load environment variables
load_dotenv()


async def run_contract_coverage(
    callable_ref: str,
    output_file: str | None = None,
    max_turns: int = 50,
    verbose: bool = True,
    debug: bool = False,
) -> ContractCoverageResult:
    """Run contract coverage rooted at a Python callable entrypoint.

    Args:
        callable_ref: Callable reference string in the form "{file.py}:{qualname}"
        output_file: Optional path to save results as JSON
        max_turns: Maximum turns for agent (default: 50)

    Returns:
        ContractCoverageResult with uncovered obligation IDs
    """
    print(f"🔍 Starting contract coverage for: {callable_ref}")
    print(f"📊 Max turns: {max_turns}")
    print()

    # Initialize LLM client
    anthropic_client = AsyncAnthropic()
    llm_client = LLMClaude(anthropic_client)

    # Create and run agent
    agent = ContractCoverageAgent(llm_client)

    if verbose:
        print("🤖 Agent starting analysis...")
        print()

    result = await agent.analyze_coverage(
        callable_ref, max_turns=max_turns, verbose=verbose
    )

    # Print summary
    print("\n" + "=" * 80)
    print("📋 COVERAGE COMPLETE")
    print("=" * 80)
    total_uncovered = len(result.uncovered_obligation_ids)
    print(f"\n🚫 Uncovered obligations: {total_uncovered}")

    if result.uncovered_obligation_ids:
        for obl_id in result.uncovered_obligation_ids:
            print(f"   - {obl_id}")

    if result.discovered_test_refs:
        print("\n🧪 Tests considered:")
        for test_ref in result.discovered_test_refs:
            print(f"   - {test_ref}")

    if result.notes:
        print("\n📝 Notes:")
        print(result.notes)

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
        description="Analyze test coverage for contract obligations rooted at a callable entrypoint"
    )
    parser.add_argument(
        "callable_ref",
        help='Callable reference string "{file.py}:{qualname}" (e.g., merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__)',
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to save results JSON file",
        default="coverage_output.json",
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

        await run_contract_coverage(
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
