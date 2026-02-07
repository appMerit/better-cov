"""AST parser for Python SUT (System Under Test) codebases.

Extracts structural information from Python source files using the built-in
ast module: classes, functions, signatures, imports, call sites, and
pipeline flow -- all without executing the code.
"""

import ast
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unparse_safe(node: ast.AST) -> str:
    """Return source-like text for an AST node, or '?' on failure."""
    try:
        return ast.unparse(node)
    except Exception:
        return "?"


def _annotation_str(node: ast.AST | None) -> str | None:
    """Convert a type-annotation AST node to a readable string."""
    if node is None:
        return None
    return _unparse_safe(node)


def _format_arg(arg: ast.arg) -> str:
    """Format a single function argument (name + optional annotation)."""
    name = arg.arg
    ann = _annotation_str(arg.annotation)
    if ann:
        return f"{name}: {ann}"
    return name


def _format_arguments(args: ast.arguments) -> list[str]:
    """Format the full argument list of a function, excluding 'self'/'cls'."""
    formatted: list[str] = []

    # Positional-only args
    for arg in args.posonlyargs:
        if arg.arg in ("self", "cls"):
            continue
        formatted.append(_format_arg(arg))

    # Regular positional/keyword args
    # Compute where defaults start
    num_regular = len(args.args)
    num_defaults = len(args.defaults)
    default_offset = num_regular - num_defaults

    for i, arg in enumerate(args.args):
        if arg.arg in ("self", "cls"):
            continue
        base = _format_arg(arg)
        di = i - default_offset
        if di >= 0 and di < len(args.defaults):
            default_val = _unparse_safe(args.defaults[di])
            base += f"={default_val}"
        formatted.append(base)

    # *args
    if args.vararg:
        formatted.append(f"*{_format_arg(args.vararg)}")

    # Keyword-only args
    for i, arg in enumerate(args.kwonlyargs):
        base = _format_arg(arg)
        if i < len(args.kw_defaults) and args.kw_defaults[i] is not None:
            default_val = _unparse_safe(args.kw_defaults[i])
            base += f"={default_val}"
        formatted.append(base)

    # **kwargs
    if args.kwarg:
        formatted.append(f"**{_format_arg(args.kwarg)}")

    return formatted


def _get_end_lineno(node: ast.AST) -> int:
    """Get the end line number of an AST node."""
    return getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)


# ---------------------------------------------------------------------------
# Call collector -- extracts function/method calls from a function body
# ---------------------------------------------------------------------------

class _CallCollector(ast.NodeVisitor):
    """Walk a function body and collect all function/method call names."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        if isinstance(func, ast.Name):
            self.calls.append(func.id)
        elif isinstance(func, ast.Attribute):
            # e.g. self.method(), obj.func()
            parts: list[str] = [func.attr]
            value = func.value
            while isinstance(value, ast.Attribute):
                parts.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                parts.append(value.id)
            parts.reverse()
            self.calls.append(".".join(parts))
        self.generic_visit(node)


def _collect_calls(body: list[ast.stmt]) -> list[str]:
    """Return deduplicated, order-preserved list of call names in a body."""
    collector = _CallCollector()
    for stmt in body:
        collector.visit(stmt)
    seen: set[str] = set()
    result: list[str] = []
    for c in collector.calls:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


# ---------------------------------------------------------------------------
# Pipeline step extractor -- sequential steps of a function body
# ---------------------------------------------------------------------------

def _extract_pipeline_steps(body: list[ast.stmt]) -> list[dict[str, Any]]:
    """Extract sequential pipeline steps from a function body.

    Each step is a top-level statement: either a conditional (if) with the
    condition text and the calls inside, or a plain call/assignment with
    its key function call.
    """
    steps: list[dict[str, Any]] = []

    for stmt in body:
        # Unwrap: if the statement is inside a `with` block, look inside it
        actual_stmts = [stmt]
        if isinstance(stmt, ast.With):
            actual_stmts = stmt.body

        for s in actual_stmts:
            step = _classify_stmt(s)
            if step:
                steps.append(step)

    return steps


def _classify_stmt(stmt: ast.stmt) -> dict[str, Any] | None:
    """Classify a single statement as a pipeline step."""
    line = getattr(stmt, "lineno", 0)

    if isinstance(stmt, ast.If):
        condition = _unparse_safe(stmt.test)
        calls_true = _collect_calls(stmt.body)
        has_else = len(stmt.orelse) > 0
        calls_else = _collect_calls(stmt.orelse) if has_else else []
        return {
            "line": line,
            "type": "if",
            "condition": condition,
            "calls": calls_true,
            "has_else": has_else,
            "else_calls": calls_else,
        }

    if isinstance(stmt, ast.With):
        # Recurse into with-body for nested pipeline steps
        inner_steps = _extract_pipeline_steps(stmt.body)
        if inner_steps:
            return {
                "line": line,
                "type": "with",
                "steps": inner_steps,
            }
        return None

    # Assignments and expressions with calls
    calls = _collect_calls([stmt])
    if calls:
        return {
            "line": line,
            "type": "call",
            "calls": calls,
        }

    if isinstance(stmt, ast.Return):
        return {
            "line": line,
            "type": "return",
            "value": _unparse_safe(stmt.value) if stmt.value else None,
        }

    return None


# ---------------------------------------------------------------------------
# Module parser
# ---------------------------------------------------------------------------

def _parse_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, Any]:
    """Parse a single function/method definition."""
    args = _format_arguments(node.args)
    return_ann = _annotation_str(node.returns)
    decorators = [_unparse_safe(d) for d in node.decorator_list]
    docstring = ast.get_docstring(node)
    calls = _collect_calls(node.body)

    return {
        "name": node.name,
        "line_start": node.lineno,
        "line_end": _get_end_lineno(node),
        "args": args,
        "return_annotation": return_ann,
        "decorators": decorators,
        "docstring": docstring,
        "calls": calls,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
    }


def _parse_class(node: ast.ClassDef) -> dict[str, Any]:
    """Parse a class definition and its methods."""
    bases = [_unparse_safe(b) for b in node.bases]
    decorators = [_unparse_safe(d) for d in node.decorator_list]
    docstring = ast.get_docstring(node)

    methods: list[dict[str, Any]] = []
    class_attrs: list[dict[str, str]] = []

    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_parse_function(item))
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            # Class-level annotated attributes (e.g., fields in a dataclass)
            attr_info: dict[str, str] = {
                "name": item.target.id,
            }
            if item.annotation:
                attr_info["annotation"] = _unparse_safe(item.annotation)
            if item.value:
                attr_info["default"] = _unparse_safe(item.value)
            class_attrs.append(attr_info)
        elif isinstance(item, ast.Assign):
            # Class-level plain assignments (e.g. name = AGENT.ERROR_ANALYZER)
            for target in item.targets:
                if isinstance(target, ast.Name):
                    class_attrs.append({
                        "name": target.id,
                        "default": _unparse_safe(item.value),
                    })

    is_dataclass = any("dataclass" in d for d in decorators)

    return {
        "name": node.name,
        "line_start": node.lineno,
        "line_end": _get_end_lineno(node),
        "bases": bases,
        "decorators": decorators,
        "docstring": docstring,
        "methods": methods,
        "class_attrs": class_attrs,
        "is_dataclass": is_dataclass,
    }


def _parse_import(node: ast.Import | ast.ImportFrom) -> list[dict[str, str]]:
    """Parse an import statement into a list of import records."""
    records: list[dict[str, str]] = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            records.append({
                "module": alias.name,
                "name": alias.asname or alias.name,
                "type": "import",
            })
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            records.append({
                "module": module,
                "name": alias.asname or alias.name,
                "original_name": alias.name,
                "type": "from_import",
            })

    return records


def parse_module(file_path: str | Path) -> dict[str, Any]:
    """Parse a single Python file and extract its structure.

    Returns a dict with:
        - path: relative file path
        - docstring: module docstring
        - line_count: total lines
        - imports: list of import records
        - classes: list of class dicts
        - functions: list of top-level function dicts
    """
    file_path = Path(file_path)
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    line_count = len(source.splitlines())

    docstring = ast.get_docstring(tree)
    imports: list[dict[str, str]] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.extend(_parse_import(node))
        elif isinstance(node, ast.ClassDef):
            classes.append(_parse_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_parse_function(node))

    return {
        "path": str(file_path),
        "docstring": docstring,
        "line_count": line_count,
        "imports": imports,
        "classes": classes,
        "functions": functions,
    }


# ---------------------------------------------------------------------------
# SUT-level parser: walk directory, parse all, resolve call graph
# ---------------------------------------------------------------------------

def _find_python_files(directory: str | Path) -> list[Path]:
    """Recursively find all .py files in a directory, sorted by path."""
    root = Path(directory)
    files = sorted(root.rglob("*.py"))
    # Skip __pycache__, .venv, etc.
    return [
        f for f in files
        if "__pycache__" not in f.parts
        and ".venv" not in f.parts
        and "node_modules" not in f.parts
    ]


def _build_symbol_table(
    modules: list[dict[str, Any]], sut_root: Path
) -> dict[str, str]:
    """Build a mapping of symbol name -> qualified name for all SUT definitions.

    E.g. { "route": "app.router:route",
            "TravelOpsAgent": "app.agent:TravelOpsAgent", ... }
    """
    table: dict[str, str] = {}

    for mod in modules:
        mod_path = Path(mod["path"]).relative_to(sut_root.parent)
        # Convert path to module-style qualifier: app/agent.py -> app.agent
        parts = list(mod_path.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].replace(".py", "")
        mod_qual = ".".join(parts)

        for func in mod["functions"]:
            qualified = f"{mod_qual}:{func['name']}"
            table[func["name"]] = qualified

        for cls in mod["classes"]:
            cls_qual = f"{mod_qual}:{cls['name']}"
            table[cls["name"]] = cls_qual
            for method in cls["methods"]:
                method_qual = f"{mod_qual}:{cls['name']}.{method['name']}"
                table[f"{cls['name']}.{method['name']}"] = method_qual

    return table


def _resolve_call_graph(
    modules: list[dict[str, Any]],
    symbol_table: dict[str, str],
) -> list[dict[str, str]]:
    """Build call graph edges by matching calls to SUT symbols.

    Returns list of { "caller": qualified, "callee": qualified | raw_name }.
    Only includes edges where at least the caller is a SUT symbol.
    """
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for mod in modules:
        for func in mod["functions"]:
            caller = symbol_table.get(func["name"], func["name"])
            for call_name in func["calls"]:
                _add_edge(edges, seen, caller, call_name, symbol_table)

        for cls in mod["classes"]:
            for method in cls["methods"]:
                caller_key = f"{cls['name']}.{method['name']}"
                caller = symbol_table.get(caller_key, caller_key)
                for call_name in method["calls"]:
                    _add_edge(edges, seen, caller, call_name, symbol_table, cls["name"])

    return edges


def _add_edge(
    edges: list[dict[str, str]],
    seen: set[tuple[str, str]],
    caller: str,
    call_name: str,
    symbol_table: dict[str, str],
    current_class: str | None = None,
) -> None:
    """Add a call-graph edge, resolving self.method and imports.

    Only adds the edge if the callee resolves to a SUT-defined symbol.
    This keeps the call graph focused on intra-SUT calls and filters out
    stdlib/third-party noise (len, str, json.dumps, etc.).
    """
    callee: str | None = None

    # Resolve self.X to ClassName.X
    if call_name.startswith("self."):
        method_name = call_name[5:]  # strip "self."
        if current_class:
            resolved_key = f"{current_class}.{method_name}"
            callee = symbol_table.get(resolved_key, None)
    else:
        # Try direct lookup
        callee = symbol_table.get(call_name, None)
        if callee is None:
            # Try just the last part (e.g. "obj.method" -> "method")
            parts = call_name.split(".")
            if len(parts) > 1:
                callee = symbol_table.get(parts[-1], None)

    # Only add if callee is a known SUT symbol
    if callee is None:
        return

    key = (caller, callee)
    if key not in seen:
        seen.add(key)
        edges.append({"caller": caller, "callee": callee})


def _extract_main_pipeline(
    modules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find the main entry-point class and extract pipeline flow from its run() method.

    Heuristic: look for the class with a `run` or `__call__` method that has
    the most lines of code.
    """
    best: dict[str, Any] | None = None
    best_size = 0

    for mod in modules:
        for cls in mod["classes"]:
            for method in cls["methods"]:
                if method["name"] in ("run", "__call__"):
                    size = method["line_end"] - method["line_start"]
                    if size > best_size:
                        best_size = size
                        best = {
                            "class_name": cls["name"],
                            "method_name": method["name"],
                            "file": mod["path"],
                            "line_start": method["line_start"],
                            "line_end": method["line_end"],
                        }

    if best is None:
        return None

    # Re-parse the specific method to get pipeline steps
    file_path = Path(best["file"])
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == best["class_name"]:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == best["method_name"]
                ):
                    steps = _extract_pipeline_steps(item.body)
                    best["steps"] = steps
                    return best

    return best


def parse_sut(directory: str | Path) -> dict[str, Any]:
    """Parse an entire SUT directory and return structured analysis.

    Returns a dict with:
        - sut_root: the directory path
        - modules: list of parsed module dicts
        - symbol_table: name -> qualified name mapping
        - call_graph: list of caller/callee edge dicts
        - pipeline: main entry-point pipeline flow (or None)
    """
    directory = Path(directory).resolve()
    py_files = _find_python_files(directory)

    modules: list[dict[str, Any]] = []
    for f in py_files:
        try:
            mod = parse_module(f)
            modules.append(mod)
        except SyntaxError:
            # Skip files that don't parse
            continue

    symbol_table = _build_symbol_table(modules, directory)
    call_graph = _resolve_call_graph(modules, symbol_table)
    pipeline = _extract_main_pipeline(modules)

    return {
        "sut_root": str(directory),
        "modules": modules,
        "symbol_table": symbol_table,
        "call_graph": call_graph,
        "pipeline": pipeline,
    }
