"""AST parser for Python SUT (System Under Test) codebases.

Extracts structural information from Python source files using the built-in
ast module: classes, functions, signatures, imports, call sites, and
pipeline flow -- all without executing the code.
"""

import ast
from pathlib import Path
from typing import Any
from collections import defaultdict


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
        default_node = args.kw_defaults[i] if i < len(args.kw_defaults) else None
        if default_node is not None:
            default_val = _unparse_safe(default_node)
            base += f"={default_val}"
        formatted.append(base)

    # **kwargs
    if args.kwarg:
        formatted.append(f"**{_format_arg(args.kwarg)}")

    return formatted


def _get_end_lineno(node: ast.AST) -> int:
    """Get the end line number of an AST node."""
    return getattr(node, "end_lineno", None) or getattr(node, "lineno", 0)


def _parse_callable_ref(callable_ref: str) -> tuple[Path, list[str]]:
    """Parse a callable reference of the form '{file.py}:{qualname}'.

    Returns:
        (file_path, qual_parts)
    """
    if ":" not in callable_ref:
        raise ValueError(
            "callable_ref must be in the form '{file.py}:{qualname}', "
            f"got: {callable_ref!r}"
        )
    file_part, qual = callable_ref.split(":", 1)
    file_path = Path(file_part).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Callable file does not exist: {str(file_path)!r}")
    if file_path.suffix != ".py":
        raise ValueError(f"Callable file must be a .py file, got: {str(file_path)!r}")
    qual = qual.strip()
    if not qual:
        raise ValueError(
            "callable_ref is missing qualname after ':', "
            f"got: {callable_ref!r}"
        )
    parts = [p.strip() for p in qual.split(".") if p.strip()]
    if not parts:
        raise ValueError(f"Invalid qualname in callable_ref: {callable_ref!r}")
    return file_path, parts


def _find_named_def_in_body(
    body: list[ast.stmt], name: str
) -> ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find a named class or function definition directly inside a body."""
    for stmt in body:
        if isinstance(stmt, ast.ClassDef) and stmt.name == name:
            return stmt
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == name:
            return stmt
    return None


def _find_qualname_node(
    tree: ast.AST, qual_parts: list[str]
) -> tuple[ast.AST, list[ast.AST]]:
    """Find an AST node by qualname parts, returning (node, parents_chain).

    The qualname is resolved purely structurally, without executing code.
    Supported containers: module, class bodies, and function bodies (nested defs).
    """
    if not isinstance(tree, ast.Module):
        raise ValueError("Expected an ast.Module for qualname resolution")

    parents: list[ast.AST] = []
    current: ast.AST = tree
    for part in qual_parts:
        body: list[ast.stmt] | None = getattr(current, "body", None)
        if body is None:
            raise ValueError(
                f"Cannot resolve qualname {'.'.join(qual_parts)!r}: "
                f"{type(current).__name__} has no body"
            )
        found = _find_named_def_in_body(body, part)
        if found is None:
            raise ValueError(
                f"Callable {'.'.join(qual_parts)!r} not found in module"
            )
        parents.append(current)
        current = found

    return current, parents


def _module_qualifier(file_path: Path, sut_root: Path) -> str:
    """Convert file path into module-style qualifier (e.g. app/agent.py -> app.agent)."""
    mod_path = file_path.relative_to(sut_root.parent)
    parts = list(mod_path.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def _module_qualifier_from_root(file_path: Path, project_root: Path) -> str:
    """Convert file path into module-style qualifier relative to a project root.

    Example:
        project_root=/repo/merit-travelops-demo
        file_path=/repo/merit-travelops-demo/app/agent.py
        -> "app.agent"
    """
    mod_path = file_path.relative_to(project_root)
    parts = list(mod_path.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].replace(".py", "")
    return ".".join(parts)


def _infer_project_root(file_path: Path) -> Path:
    """Infer a sensible project root for callable-rooted parsing.

    Walks upward looking for common Python project markers.
    Falls back to the file's parent directory if nothing is found.
    """
    markers = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
    for parent in [file_path.parent, *file_path.parents]:
        for m in markers:
            if (parent / m).exists():
                return parent
    return file_path.parent


def _build_symbol_index(modules: list[dict[str, Any]], project_root: Path) -> dict[str, set[str]]:
    """Build a multi-mapping of symbol key -> set of qualified names.

    Keys include:
      - function name: "foo"
      - class name: "MyClass"
      - method qual key: "MyClass.run"
      - method short key: "run" (for unique-name heuristic only)
    """
    index: dict[str, set[str]] = defaultdict(set)

    for mod in modules:
        file_path = Path(mod["path"])
        mod_qual = _module_qualifier_from_root(file_path, project_root)

        for func in mod.get("functions", []):
            q = f"{mod_qual}:{func['name']}"
            index[func["name"]].add(q)

        for cls in mod.get("classes", []):
            cq = f"{mod_qual}:{cls['name']}"
            index[cls["name"]].add(cq)

            for method in cls.get("methods", []):
                key = f"{cls['name']}.{method['name']}"
                mq = f"{mod_qual}:{key}"
                index[key].add(mq)
                # Also index bare method name to enable unique-name resolution for attribute calls.
                index[method["name"]].add(mq)

    return dict(index)


def _resolve_unique(index: dict[str, set[str]], key: str) -> str | None:
    """Resolve a symbol key to a unique qualified name, else None."""
    cands = index.get(key)
    if not cands:
        return None
    if len(cands) == 1:
        return next(iter(cands))
    return None


def _resolve_callee_qualified(
    call_name: str,
    index: dict[str, set[str]],
    current_class: str | None = None,
) -> str | None:
    """Resolve a call name to a unique qualified SUT symbol (or None).

    Heuristics:
      - self.method  (where current_class is known) -> Class.method
      - exact match
      - last token (attribute call): obj.method -> method (only if unique in project)
    """
    parts = call_name.split(".")

    # Strict self.<method> resolution for intra-class calls
    if call_name.startswith("self.") and current_class and len(parts) == 2:
        maybe = _resolve_unique(index, f"{current_class}.{parts[1]}")
        if maybe:
            return maybe

    # Exact match (rare but possible if call collector yields simple names)
    maybe = _resolve_unique(index, call_name)
    if maybe:
        return maybe

    # Attribute/method call: resolve by last token if unique in project
    if len(parts) > 1:
        maybe = _resolve_unique(index, parts[-1])
        if maybe:
            return maybe

    # Simple name call: resolve if unique
    return _resolve_unique(index, call_name)


def _resolve_call_graph_rooted(
    modules: list[dict[str, Any]],
    project_root: Path,
    index: dict[str, set[str]],
) -> list[dict[str, str]]:
    """Resolve call graph edges across a project rooted at project_root.

    Adds an edge only when the callee resolves uniquely to a SUT symbol.
    """
    edges: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for mod in modules:
        file_path = Path(mod["path"])
        mod_qual = _module_qualifier_from_root(file_path, project_root)

        for func in mod.get("functions", []):
            caller = f"{mod_qual}:{func['name']}"
            for call_name in func.get("calls", []):
                callee = _resolve_callee_qualified(call_name, index)
                if not callee:
                    continue
                key = (caller, callee)
                if key not in seen:
                    seen.add(key)
                    edges.append({"caller": caller, "callee": callee})

        for cls in mod.get("classes", []):
            for method in cls.get("methods", []):
                caller = f"{mod_qual}:{cls['name']}.{method['name']}"
                for call_name in method.get("calls", []):
                    callee = _resolve_callee_qualified(call_name, index, current_class=cls["name"])
                    if not callee:
                        continue
                    key = (caller, callee)
                    if key not in seen:
                        seen.add(key)
                        edges.append({"caller": caller, "callee": callee})

    return edges


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
            caller = str(symbol_table.get(func["name"], func["name"]))
            for call_name in func["calls"]:
                _add_edge(edges, seen, caller, call_name, symbol_table)

        for cls in mod["classes"]:
            for method in cls["methods"]:
                caller_key = f"{cls['name']}.{method['name']}"
                caller = str(symbol_table.get(caller_key, caller_key))
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


# ---------------------------------------------------------------------------
# Callable-rooted parser
# ---------------------------------------------------------------------------

def parse_callable(callable_ref: str) -> dict[str, Any]:
    """Parse a single Python file and return analysis rooted at a callable.

    The callable is identified by a reference string: "{file.py}:{qualname}".
    The resulting structure is filtered to only include definitions that are
    reachable from the entry callable via intra-file call graph edges.
    """
    file_path, qual_parts = _parse_callable_ref(callable_ref)
    project_root = _infer_project_root(file_path).resolve()

    py_files = _find_python_files(project_root)
    modules: list[dict[str, Any]] = []
    for f in py_files:
        try:
            modules.append(parse_module(f))
        except SyntaxError:
            continue

    index = _build_symbol_index(modules, project_root)
    call_graph_all = _resolve_call_graph_rooted(modules, project_root, index)

    # Locate the entry node to determine whether this is a function/method/class
    source = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(file_path))
    entry_node, parents = _find_qualname_node(tree, qual_parts)

    entry_type: str
    entry_qualname: str
    entry_pipeline_target: tuple[str, str] | None = None  # (class_name, method_name) for methods

    if isinstance(entry_node, ast.ClassDef):
        entry_type = "class"
        entry_qualname = f"{_module_qualifier_from_root(file_path, project_root)}:{entry_node.name}"
        # For reachability/pipeline, prefer __call__ then run if present
        preferred = None
        for mname in ("__call__", "run"):
            if any(
                isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and s.name == mname
                for s in entry_node.body
            ):
                preferred = mname
                break
        if preferred:
            entry_pipeline_target = (entry_node.name, preferred)
    elif isinstance(entry_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # If parent is a class, treat as method; otherwise function
        parent = parents[-1] if parents else None
        if isinstance(parent, ast.ClassDef):
            entry_type = "method"
            entry_qualname = f"{_module_qualifier_from_root(file_path, project_root)}:{parent.name}.{entry_node.name}"
            entry_pipeline_target = (parent.name, entry_node.name)
        else:
            entry_type = "function"
            entry_qualname = f"{_module_qualifier_from_root(file_path, project_root)}:{entry_node.name}"
    else:
        raise ValueError(
            f"Resolved node for {callable_ref!r} is not a callable definition: "
            f"{type(entry_node).__name__}"
        )

    # Choose graph root for reachability: method preferred for class entry
    graph_root = entry_qualname
    if entry_type == "class" and entry_pipeline_target:
        cname, mname = entry_pipeline_target
        graph_root = f"{_module_qualifier_from_root(file_path, project_root)}:{cname}.{mname}"

    # Compute reachable set by BFS over call graph starting at root
    adjacency: dict[str, list[str]] = {}
    for edge in call_graph_all:
        adjacency.setdefault(edge["caller"], []).append(edge["callee"])

    reachable: set[str] = set()
    queue: list[str] = [graph_root]
    while queue:
        cur = queue.pop(0)
        if cur in reachable:
            continue
        reachable.add(cur)
        for nxt in adjacency.get(cur, []):
            if nxt not in reachable:
                queue.append(nxt)

    # Always include the class itself if the entry is a class/method
    if entry_type == "class":
        reachable.add(entry_qualname)
    if entry_type == "method" and isinstance(parents[-1], ast.ClassDef):
        reachable.add(f"{_module_qualifier_from_root(file_path, project_root)}:{parents[-1].name}")

    # Filter call graph down to reachable portion
    call_graph = [e for e in call_graph_all if e["caller"] in reachable and e["callee"] in reachable]

    # Filter module definitions down to reachable portion (callable-rooted tree)
    filtered_modules: list[dict[str, Any]] = []
    for mod in modules:
        mpath = Path(mod["path"])
        mqual = _module_qualifier_from_root(mpath, project_root)

        filtered_functions: list[dict[str, Any]] = []
        for func in mod.get("functions", []):
            qn = f"{mqual}:{func['name']}"
            if qn in reachable:
                filtered_functions.append(func)

        filtered_classes: list[dict[str, Any]] = []
        for cls in mod.get("classes", []):
            cls_qn = f"{mqual}:{cls['name']}"
            method_filtered: list[dict[str, Any]] = []
            for m in cls.get("methods", []):
                m_qn = f"{mqual}:{cls['name']}.{m['name']}"
                if m_qn in reachable:
                    method_filtered.append(m)

            if cls_qn in reachable or method_filtered:
                kept = dict(cls)
                kept["methods"] = method_filtered
                filtered_classes.append(kept)

        if filtered_functions or filtered_classes:
            kept_mod = dict(mod)
            kept_mod["functions"] = filtered_functions
            kept_mod["classes"] = filtered_classes
            filtered_modules.append(kept_mod)

    # Pipeline steps for entry callable (function/method), or preferred method for class entry
    pipeline: dict[str, Any] | None = None
    pipeline_callable: str | None = None
    pipeline_node: ast.AST | None = None

    if entry_type in ("function", "method"):
        pipeline_node = entry_node
        pipeline_callable = entry_qualname.split(":", 1)[1]
    elif entry_type == "class" and entry_pipeline_target:
        cname, mname = entry_pipeline_target
        pipeline_callable = f"{cname}.{mname}"
        # Find method node again inside class
        for stmt in entry_node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == mname:
                pipeline_node = stmt
                break

    if isinstance(pipeline_node, (ast.FunctionDef, ast.AsyncFunctionDef)) and pipeline_callable:
        pipeline = {
            "callable": pipeline_callable,
            "file": str(file_path),
            "line_start": pipeline_node.lineno,
            "line_end": _get_end_lineno(pipeline_node),
            "steps": _extract_pipeline_steps(pipeline_node.body),
        }

    entry_doc = ast.get_docstring(entry_node) if isinstance(
        entry_node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    ) else None

    entrypoint = {
        "type": entry_type,
        "callable": entry_qualname.split(":", 1)[1],
        "qualified": entry_qualname,
        "file": str(file_path),
        "line_start": getattr(entry_node, "lineno", 0),
        "line_end": _get_end_lineno(entry_node),
        "docstring": entry_doc,
    }

    return {
        "sut_root": str(project_root),
        "display_root": str(project_root),
        "entrypoint": entrypoint,
        "modules": filtered_modules,
        "symbol_table": {},  # legacy field; not used by formatter in callable-rooted mode
        "call_graph": call_graph,
        "pipeline": pipeline,
    }
