"""AST-based SUT analyzer for generating LLM agent context.

Public API:
    extract_sut_ast(sut_path) -> str
        Parse a Python SUT directory and return an LLM-readable structural
        map of the codebase (files, classes, functions, call graph, pipeline).
"""

from .formatter import format_sut_ast
from .parser import parse_sut


def extract_sut_ast(sut_path: str) -> str:
    """Parse a Python SUT directory and return LLM-readable AST context.

    Args:
        sut_path: Path to the SUT source directory (e.g. 'merit-travelops-demo/app').

    Returns:
        A structured text block describing the SUT's code structure,
        ready to be injected into an LLM agent's prompt context.
    """
    parsed = parse_sut(sut_path)
    return format_sut_ast(parsed)


__all__ = ["extract_sut_ast", "parse_sut", "format_sut_ast"]
