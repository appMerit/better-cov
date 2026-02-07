"""Format parsed SUT AST data into LLM-readable text for agent context.

Produces a concise, structured text block that gives an LLM agent a complete
map of the SUT: files, classes, functions, call graph, and pipeline flow.
"""

from pathlib import Path
from typing import Any


def format_sut_ast(parsed: dict[str, Any]) -> str:
    """Convert parsed SUT data into an LLM-readable text block.

    Args:
        parsed: Output of parse_sut() -- dict with modules, call_graph, pipeline, etc.

    Returns:
        A multi-section text string ready to be injected into an agent prompt.
    """
    sections: list[str] = []
    sut_root = Path(parsed["sut_root"])

    sections.append("## SUT Code Map\n")
    sections.append(_format_files_section(parsed["modules"], sut_root))
    sections.append(_format_classes_section(parsed["modules"], sut_root))
    sections.append(_format_functions_section(parsed["modules"], sut_root))
    sections.append(_format_call_graph_section(parsed["call_graph"]))

    if parsed.get("pipeline"):
        sections.append(_format_pipeline_section(parsed["pipeline"], sut_root))

    # Mermaid execution flow diagram
    if parsed.get("pipeline"):
        sections.append(
            _format_mermaid_pipeline(parsed["pipeline"], parsed["call_graph"])
        )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Section formatters
# ---------------------------------------------------------------------------

def _rel_path(abs_path: str, sut_root: Path) -> str:
    """Get a relative path from the SUT root's parent for display."""
    try:
        return str(Path(abs_path).relative_to(sut_root.parent))
    except ValueError:
        return abs_path


def _format_files_section(modules: list[dict[str, Any]], sut_root: Path) -> str:
    """Format the Files section listing all SUT modules."""
    lines = ["### Files"]
    for mod in modules:
        rel = _rel_path(mod["path"], sut_root)
        doc = mod.get("docstring") or ""
        # Take first sentence of docstring
        if doc:
            doc = doc.split("\n")[0].strip().rstrip(".")
        line_count = mod.get("line_count", 0)
        entry = f"- {rel} ({line_count} lines)"
        if doc:
            entry += f" - {doc}"
        lines.append(entry)
    return "\n".join(lines) + "\n"


def _format_classes_section(modules: list[dict[str, Any]], sut_root: Path) -> str:
    """Format the Classes section with methods and attributes."""
    lines = ["### Classes"]
    has_classes = False

    for mod in modules:
        rel = _rel_path(mod["path"], sut_root)
        for cls in mod.get("classes", []):
            has_classes = True
            line_range = f"{cls['line_start']}-{cls['line_end']}"
            tags: list[str] = []
            if cls.get("is_dataclass"):
                tags.append("dataclass")
            if cls.get("bases"):
                tags.append(f"extends {', '.join(cls['bases'])}")
            tag_str = f" [{', '.join(tags)}]" if tags else ""

            lines.append(f"- {cls['name']} ({rel}:{line_range}){tag_str}")

            # Methods
            if cls.get("methods"):
                method_sigs: list[str] = []
                for m in cls["methods"]:
                    args_str = ", ".join(m["args"])
                    method_sigs.append(f"{m['name']}({args_str})")
                lines.append(f"    methods: {', '.join(method_sigs)}")

            # Dataclass fields / class attributes
            if cls.get("is_dataclass") and cls.get("class_attrs"):
                field_names = [a["name"] for a in cls["class_attrs"]]
                lines.append(f"    fields: {', '.join(field_names)}")

    if not has_classes:
        lines.append("(none)")

    return "\n".join(lines) + "\n"


def _format_functions_section(modules: list[dict[str, Any]], sut_root: Path) -> str:
    """Format the Functions section with signatures and locations."""
    lines = ["### Functions"]
    has_funcs = False

    for mod in modules:
        rel = _rel_path(mod["path"], sut_root)
        for func in mod.get("functions", []):
            has_funcs = True
            args_str = ", ".join(func["args"])
            ret = func.get("return_annotation")
            sig = f"{func['name']}({args_str})"
            if ret:
                sig += f" -> {ret}"
            line_range = f"{func['line_start']}-{func['line_end']}"
            lines.append(f"- {sig}  ({rel}:{line_range})")

    if not has_funcs:
        lines.append("(none)")

    return "\n".join(lines) + "\n"


def _format_call_graph_section(call_graph: list[dict[str, str]]) -> str:
    """Format the Call Graph section showing who calls whom.

    Groups edges by caller and only shows callers that have SUT-internal callees.
    Uses short names for readability.
    """
    lines = ["### Call Graph (who calls whom)"]

    if not call_graph:
        lines.append("(no internal calls detected)")
        return "\n".join(lines) + "\n"

    # Group by caller
    grouped: dict[str, list[str]] = {}
    for edge in call_graph:
        caller = _short_name(edge["caller"])
        callee = _short_name(edge["callee"])
        grouped.setdefault(caller, []).append(callee)

    for caller, callees in grouped.items():
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for c in callees:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        lines.append(f"{caller}  ->  {', '.join(unique)}")

    return "\n".join(lines) + "\n"


def _format_pipeline_section(pipeline: dict[str, Any], sut_root: Path) -> str:
    """Format the Pipeline Flow section showing the main entry point's steps."""
    cls_name = pipeline.get("class_name", "?")
    method_name = pipeline.get("method_name", "?")
    rel = _rel_path(pipeline.get("file", ""), sut_root)

    lines = [f"### Pipeline Flow ({cls_name}.{method_name})"]
    lines.append(f"Source: {rel}:{pipeline.get('line_start', '?')}-{pipeline.get('line_end', '?')}")

    steps = pipeline.get("steps", [])
    _format_steps(steps, lines, step_num=[1], indent=0)

    return "\n".join(lines) + "\n"


def _format_steps(
    steps: list[dict[str, Any]],
    lines: list[str],
    step_num: list[int],
    indent: int = 0,
) -> None:
    """Recursively format pipeline steps into numbered lines."""
    prefix = "  " * indent

    for step in steps:
        line_ref = f"L{step.get('line', '?')}"
        stype = step.get("type", "?")

        if stype == "if":
            condition = step.get("condition", "?")
            calls = step.get("calls", [])
            has_else = step.get("has_else", False)
            else_calls = step.get("else_calls", [])

            call_str = ", ".join(_short_name(c) for c in calls) if calls else ""
            entry = f"{prefix}{step_num[0]}. [{line_ref}] if {condition}"
            if call_str:
                entry += f" -> {call_str}"
            if has_else:
                else_str = ", ".join(_short_name(c) for c in else_calls) if else_calls else "fallback"
                entry += f" ELSE -> {else_str}"
            lines.append(entry)
            step_num[0] += 1

        elif stype == "call":
            calls = step.get("calls", [])
            call_str = ", ".join(_short_name(c) for c in calls)
            lines.append(f"{prefix}{step_num[0]}. [{line_ref}] {call_str}")
            step_num[0] += 1

        elif stype == "return":
            value = step.get("value", "")
            lines.append(f"{prefix}{step_num[0]}. [{line_ref}] return {value}")
            step_num[0] += 1

        elif stype == "with":
            # Recurse into with-block steps
            inner = step.get("steps", [])
            _format_steps(inner, lines, step_num, indent)


# ---------------------------------------------------------------------------
# Mermaid diagram
# ---------------------------------------------------------------------------

def _format_mermaid_pipeline(
    pipeline: dict[str, Any],
    call_graph: list[dict[str, str]],
) -> str:
    """Generate a Mermaid flowchart showing the pipeline execution flow.

    Combines the sequential pipeline steps with call graph edges to produce
    a diagram that shows the full execution flow including sub-calls.
    """
    cls_name = pipeline.get("class_name", "Unknown")
    method_name = pipeline.get("method_name", "run")
    steps = pipeline.get("steps", [])

    lines = [f"### Execution Flow Diagram ({cls_name}.{method_name})", "```mermaid", "flowchart TD"]

    # Entry node
    entry_id = f"{cls_name}_{method_name}"
    lines.append(f'    {entry_id}["{cls_name}.{method_name}()"]')

    # Build sub-call lookup from call graph for _execute_tools, build_messages, update_session_memory
    subcall_map = _build_subcall_map(call_graph, cls_name)

    # Track node IDs we've created for deduplication
    node_counter = [0]

    for step in steps:
        _emit_mermaid_step(lines, step, entry_id, subcall_map, node_counter, cls_name)

    lines.append("```\n")
    return "\n".join(lines)


def _build_subcall_map(
    call_graph: list[dict[str, str]], main_class: str
) -> dict[str, list[str]]:
    """Build a map of function -> its SUT sub-calls for expanding key nodes.

    Only expands functions that have interesting sub-calls (not just trace_operation).
    """
    grouped: dict[str, list[str]] = {}
    for edge in call_graph:
        caller = _short_name(edge["caller"])
        callee = _short_name(edge["callee"])
        # Skip trace_operation -- it's instrumentation, not logic
        if callee == "trace_operation":
            continue
        grouped.setdefault(caller, []).append(callee)

    return grouped


def _mermaid_node_id(label: str, counter: list[int]) -> str:
    """Generate a unique Mermaid-safe node ID."""
    counter[0] += 1
    # Sanitize: replace dots, parens, spaces with underscores
    safe = label.replace(".", "_").replace("(", "").replace(")", "")
    safe = safe.replace(" ", "_").replace("'", "").replace('"', "")
    safe = safe.replace(",", "").replace("=", "_")
    return f"n{counter[0]}_{safe}"


def _mermaid_label(text: str) -> str:
    """Escape a label for Mermaid node labels.

    Strips characters that break Mermaid parsing inside node shapes.
    """
    text = text.replace('"', "")
    text = text.replace("'", "")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("{", "")
    text = text.replace("}", "")
    # Collapse multiple spaces
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


def _emit_mermaid_step(
    lines: list[str],
    step: dict[str, Any],
    parent_id: str,
    subcall_map: dict[str, list[str]],
    counter: list[int],
    main_class: str,
) -> None:
    """Emit Mermaid lines for a single pipeline step."""
    line_ref = f"L{step.get('line', '?')}"
    stype = step.get("type", "?")

    if stype == "if":
        condition = step.get("condition", "?")
        calls = step.get("calls", [])
        has_else = step.get("has_else", False)
        else_calls = step.get("else_calls", [])

        # Pick the primary SUT call (skip builtins like str, uuid)
        primary_calls = _filter_sut_calls(calls)
        primary_name = primary_calls[0] if primary_calls else "proceed"

        # Create the branch node (diamond/rhombus shape)
        cond_short = _shorten_condition(condition)
        branch_id = _mermaid_node_id(f"if_{cond_short}", counter)
        label = _mermaid_label(cond_short)
        lines.append(f"    {branch_id}{{{label}}}")
        lines.append(f"    {parent_id} --> {branch_id}")

        # True path
        if primary_calls:
            for call_name in primary_calls:
                call_display = _clean_call_name(call_name)
                true_id = _mermaid_node_id(call_display, counter)
                lines.append(f'    {true_id}["{_mermaid_label(call_display)}()"]')
                lines.append(f'    {branch_id} -->|Yes| {true_id}')
                # Expand sub-calls if this function has them
                _emit_subcalls(lines, call_display, subcall_map, true_id, counter, main_class)

        # Else path
        if has_else:
            if else_calls:
                else_primary = _filter_sut_calls(else_calls)
                for call_name in else_primary:
                    call_display = _clean_call_name(call_name)
                    else_id = _mermaid_node_id(call_display, counter)
                    lines.append(f'    {else_id}["{_mermaid_label(call_display)}()"]')
                    lines.append(f'    {branch_id} -->|No| {else_id}')
            else:
                fallback_id = _mermaid_node_id("fallback", counter)
                lines.append(f'    {fallback_id}["fallback"]')
                lines.append(f'    {branch_id} -->|No| {fallback_id}')

    elif stype == "call":
        calls = step.get("calls", [])
        primary_calls = _filter_sut_calls(calls)
        for call_name in primary_calls:
            call_display = _clean_call_name(call_name)
            node_id = _mermaid_node_id(call_display, counter)
            lines.append(f'    {node_id}["{_mermaid_label(call_display)}()"]')
            lines.append(f'    {parent_id} --> {node_id}')
            _emit_subcalls(lines, call_display, subcall_map, node_id, counter, main_class)

    elif stype == "return":
        ret_id = _mermaid_node_id("return", counter)
        value = step.get("value", "response")
        lines.append(f'    {ret_id}(["return {_mermaid_label(value)}"])')
        lines.append(f'    {parent_id} --> {ret_id}')

    elif stype == "with":
        inner = step.get("steps", [])
        for inner_step in inner:
            _emit_mermaid_step(lines, inner_step, parent_id, subcall_map, counter, main_class)


def _emit_subcalls(
    lines: list[str],
    func_name: str,
    subcall_map: dict[str, list[str]],
    parent_id: str,
    counter: list[int],
    main_class: str,
) -> None:
    """Expand a function node with its sub-calls from the call graph."""
    # Try different key forms: "Class.method" or just "function"
    subcalls = subcall_map.get(f"{main_class}.{func_name}", None)
    if subcalls is None:
        subcalls = subcall_map.get(func_name, None)
    if not subcalls:
        return

    for sub in subcalls:
        sub_display = _clean_call_name(sub)
        # Skip self-referential or already-shown
        if sub_display == func_name:
            continue
        sub_id = _mermaid_node_id(f"sub_{sub_display}", counter)
        lines.append(f'    {sub_id}["{_mermaid_label(sub_display)}()"]')
        lines.append(f'    {parent_id} --> {sub_id}')


def _filter_sut_calls(calls: list[str]) -> list[str]:
    """Filter out obvious builtins/stdlib from call lists for diagram clarity."""
    builtins = {
        "str", "int", "float", "bool", "list", "dict", "set", "tuple",
        "len", "print", "isinstance", "type", "range", "enumerate",
        "any", "all", "min", "max", "sorted", "zip", "map", "filter",
        "uuid.uuid4", "uuid4", "append", "get", "items", "keys",
        "values", "split", "join", "strip", "lower", "upper", "replace",
        "format", "encode", "decode", "startswith", "endswith",
        "hexdigest", "next",
    }
    # Also filter out method calls on non-SUT objects (e.g. response.model_dump)
    skip_prefixes = {
        "response.", "result.", "results.", "session_data.",
        "routing_decision.", "span.", "prefs.", "f.", "json.",
        "hashlib.", "os.", "time.", "re.",
    }
    result = []
    for c in calls:
        name = c.split(".")[-1] if "." in c else c
        if name in builtins or c in builtins:
            continue
        if any(c.startswith(p) for p in skip_prefixes):
            continue
        result.append(c)
    return result


def _clean_call_name(name: str) -> str:
    """Clean up a call name for display in the diagram."""
    # Strip self. prefix
    if name.startswith("self."):
        name = name[5:]
    # Strip module prefix if present
    if ":" in name:
        name = name.split(":", 1)[1]
    return name


def _shorten_condition(condition: str) -> str:
    """Shorten a condition string for diagram readability.

    Simplifies verbose conditions like 'self.config.enable_memory' to
    'enable_memory' and truncates long conditions.
    """
    # Strip self.config. prefix for readability
    condition = condition.replace("self.config.", "")
    condition = condition.replace("self.", "")
    # Simplify .get() calls: routing_decision.get('needs_tools', False) -> needs_tools
    import re
    condition = re.sub(r"\w+\.get\(['\"](\w+)['\"],\s*\w+\)", r"\1", condition)
    # Trim long conditions
    if len(condition) > 45:
        condition = condition[:42] + "..."
    return condition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _short_name(qualified: str) -> str:
    """Shorten a qualified name for readability.

    'app.agent:TravelOpsAgent.run' -> 'TravelOpsAgent.run'
    'app.router:route' -> 'route'
    'self.llm_client.generate' -> 'llm_client.generate'
    """
    # Strip module prefix (everything before and including ':')
    if ":" in qualified:
        qualified = qualified.split(":", 1)[1]
    return qualified
