"""CLI entrypoint for contract discovery + coverage."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from textwrap import shorten

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install as install_rich_traceback

from app.models.contract import ContractDiscoveryResult, ContractCoverageResult
from app.services.contract_coverage import ContractCoverageAgent
from app.services.contract_discovery import ContractDiscoveryAgent
from app.services.llm_driver.anthropic_handler import LLMClaude


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _results_dir() -> Path:
    return _repo_root() / "results"


def _save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _obligation_index(contracts: ContractDiscoveryResult) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for contract in contracts.contracts:
        for obligation in contract.obligations:
            index[obligation.id] = {
                "contract": contract.name,
                "description": obligation.description,
                "location": obligation.location,
                "enforcement": str(obligation.enforcement),
                "severity": str(obligation.severity),
            }
    return index


def _render_header(console: Console, callable_ref: str, max_turns: int) -> None:
    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold")
    header.add_column()
    header.add_row("Callable", callable_ref)
    header.add_row("Max turns", str(max_turns))
    console.print(Panel(header, title="Contract Analysis", box=box.ROUNDED))


def _render_discovery_summary(
    console: Console, contracts: ContractDiscoveryResult, sample_size: int = 3
) -> None:
    total_contracts = len(contracts.contracts)
    obligations = [obl for c in contracts.contracts for obl in c.obligations]
    total_obligations = len(obligations)

    summary = Table(box=box.SIMPLE, show_header=False)
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Contracts discovered", str(total_contracts))
    summary.add_row("Obligations discovered", str(total_obligations))
    console.print(Panel(summary, title="Discovery Summary"))

    if obligations:
        sample_table = Table(
            title=f"Sample obligations (first {min(sample_size, len(obligations))})",
            box=box.SIMPLE,
        )
        sample_table.add_column("ID", style="bold")
        sample_table.add_column("Severity")
        sample_table.add_column("Enforcement")
        sample_table.add_column("Location")
        sample_table.add_column("Description")
        for obligation in obligations[:sample_size]:
            sample_table.add_row(
                obligation.id,
                str(obligation.severity),
                str(obligation.enforcement),
                obligation.location,
                shorten(obligation.description, width=80, placeholder="..."),
            )
        console.print(sample_table)


def _render_coverage_summary(
    console: Console,
    coverage: ContractCoverageResult,
    obligation_index: dict[str, dict[str, str]],
    max_rows: int = 10,
) -> None:
    uncovered_ids = coverage.uncovered_obligation_ids
    total_obligations = len(obligation_index)
    uncovered_count = len(uncovered_ids)
    covered_count = max(total_obligations - uncovered_count, 0)
    covered_pct = (
        (covered_count / total_obligations) * 100 if total_obligations else 0.0
    )

    summary = Table(box=box.SIMPLE, show_header=False)
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Total obligations", str(total_obligations))
    summary.add_row("Covered obligations", f"{covered_count} ({covered_pct:.1f}%)")
    summary.add_row("Uncovered obligations", str(uncovered_count))
    console.print(Panel(summary, title="Coverage Summary"))

    if uncovered_ids:
        table = Table(
            title=f"Uncovered obligations (showing {min(max_rows, uncovered_count)})",
            box=box.SIMPLE,
        )
        table.add_column("ID", style="bold")
        table.add_column("Severity")
        table.add_column("Enforcement")
        table.add_column("Location")
        table.add_column("Description")
        for obl_id in uncovered_ids[:max_rows]:
            meta = obligation_index.get(
                obl_id,
                {
                    "description": "Unknown obligation ID",
                    "location": "-",
                    "enforcement": "-",
                    "severity": "-",
                },
            )
            table.add_row(
                obl_id,
                meta["severity"],
                meta["enforcement"],
                meta["location"],
                shorten(meta["description"], width=80, placeholder="..."),
            )
        console.print(table)

    if coverage.discovered_test_refs:
        tests_table = Table(
            title=f"Tests considered ({len(coverage.discovered_test_refs)})",
            box=box.SIMPLE,
            \
            show_header=False,
        )
        tests_table.add_column()
        for test_ref in coverage.discovered_test_refs[:10]:
            tests_table.add_row(test_ref)
        if len(coverage.discovered_test_refs) > 10:
            tests_table.add_row("...")
        console.print(tests_table)

    if coverage.notes:
        console.print(Panel(coverage.notes, title="Coverage Notes", box=box.SIMPLE))


async def _amain(args: argparse.Namespace) -> int:
    console = Console()
    if args.debug:
        install_rich_traceback(show_locals=True)

    _render_header(console, args.callable_ref, args.max_turns)

    load_dotenv()
    anthropic_client = AsyncAnthropic()
    llm_client = LLMClaude(anthropic_client)

    discovery_agent = ContractDiscoveryAgent(llm_client, console=console)
    coverage_agent = ContractCoverageAgent(llm_client)

    with console.status("Running contract discovery...", spinner="dots"):
        discovery = await discovery_agent.discover_contracts(
            args.callable_ref, max_turns=args.max_turns, verbose=not args.quiet
        )

    contracts_path = _results_dir() / "contracts.json"
    _save_json(contracts_path, discovery.model_dump())

    obligation_index = _obligation_index(discovery)
    _render_discovery_summary(console, discovery)

    with console.status("Running coverage analysis...", spinner="dots"):
        coverage = await coverage_agent.analyze_coverage(
            args.callable_ref, max_turns=args.max_turns, verbose=not args.quiet
        )

    coverage_path = _results_dir() / "coverage.json"
    _save_json(coverage_path, coverage.model_dump())

    _render_coverage_summary(console, coverage, obligation_index)
    console.print(
        Panel(
            f"Saved discovery results to {contracts_path}\n"
            f"Saved coverage results to {coverage_path}",
            title="Outputs",
            box=box.ROUNDED,
        )
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run contract discovery then coverage for a callable entrypoint."
    )
    parser.add_argument(
        "callable_ref",
        help='Callable reference string "{file.py}:{qualname}" '
        '(e.g., merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__)',
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
        help="Suppress agent progress logging",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed debug information",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()