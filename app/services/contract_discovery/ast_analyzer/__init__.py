"""AST-based SUT analyzer for generating LLM agent context.

Public API:
    extract_sut_ast(callable_ref) -> str
        Parse a Python module and return an LLM-readable structural map rooted
        at a specific callable (function/method/class).

Callable reference format:
    "{path/to/file.py}:{qualname}"
        qualname examples:
          - "main"
          - "MyClass"
          - "MyClass.run"
          - "outer.inner"
"""

from .formatter import format_sut_ast
from .parser import parse_callable, parse_sut


def extract_sut_ast(callable_ref: str) -> str:
    """Parse a Python callable and return LLM-readable AST context.

    Args:
        callable_ref: Callable reference string in the form "{file.py}:{qualname}".

    Returns:
        A structured text block describing the SUT's code structure,
        ready to be injected into an LLM agent's prompt context.
    """
    parsed = parse_callable(callable_ref)
    return format_sut_ast(parsed)


__all__ = ["extract_sut_ast", "parse_callable", "parse_sut", "format_sut_ast"]
