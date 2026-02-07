#!/usr/bin/env python3
"""
Extract failure signature from Merit database.

Queries Merit database for test execution details and trace spans,
then extracts a structured signature with both clustering features
and fix generation context.

Usage:
    python3 scripts/extract_failure_signature.py <case_id> [db_path]
    
    db_path defaults to .merit/merit.db
"""
import json
import sqlite3
import sys
from pathlib import Path


def get_case_info(case_id, db_path):
    """Get test case information from Merit database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get test execution info
        cursor.execute("""
            SELECT 
                execution_id,
                trace_id,
                status,
                test_name,
                file_path,
                error_message
            FROM test_executions
            WHERE case_id = ?
        """, (case_id,))
        
        row = cursor.fetchone()
        
        if not row:
            print(f"Warning: case_id {case_id} not found in test_executions", file=sys.stderr)
            conn.close()
            return None
    except Exception as e:
        print(f"Error querying test_executions for case {case_id}: {e}", file=sys.stderr)
        return None
    
    execution_id, trace_id, status, test_name, file_path, error_message = row
    
    # Get ALL assertions for this test (passed and failed)
    # We need all assertions to create the cluster key
    cursor.execute("""
        SELECT 
            expression_repr,
            passed,
            error_message,
            id
        FROM assertions
        WHERE test_execution_id = ?
        ORDER BY id
    """, (execution_id,))
    
    assertion_rows = cursor.fetchall()
    conn.close()
    
    # Parse assertions and create pretty format for clustering
    all_assertions_pretty = []
    failed_assertions = []
    
    for expr_repr_str, passed, err_msg, id in assertion_rows:
        # Parse JSON expression_repr
        try:
            expr_repr = json.loads(expr_repr_str) if expr_repr_str else {}
        except (json.JSONDecodeError, TypeError):
            # Fallback for old format (plain string)
            expr_repr = {"expr": expr_repr_str} if expr_repr_str else {}
        
        # Create pretty format (like Merit's AssertionResult.pretty)
        pretty = _format_assertion_pretty(expr_repr, passed, err_msg)
        all_assertions_pretty.append(pretty)
        
        # Track failed assertions separately for fix_context
        if not passed:
            failed_assertions.append({
                'expression': expr_repr.get('expr', ''),
                'error': err_msg,
                'resolved_args': expr_repr.get('resolved_args', {}),
                'pretty': pretty
            })
    
    return {
        'trace_id': trace_id,
        'status': status,
        'test_name': test_name,
        'test_module': file_path,
        'error_message': error_message,
        'all_assertions_pretty': all_assertions_pretty,  # For clustering key
        'failed_assertions': failed_assertions  # Detailed for fix generation
    }


def _format_assertion_pretty(expr_repr: dict, passed: bool, error_message: str | None) -> str:
    """
    Format assertion in pretty format (matching Merit's AssertionResult.pretty).
    
    Args:
        expr_repr: Dict with 'expr', 'lines_above', 'lines_below', 'resolved_args'
        passed: Whether assertion passed
        error_message: Error message if failed
        
    Returns:
        Pretty-formatted assertion string
    """
    import re
    import textwrap
    
    parts = ["Assertion Passed!" if passed else "Assertion Failed!"]
    
    if error_message:
        parts.append(f"Error message: {error_message}")
    
    # Get lines
    lines_above_str = expr_repr.get('lines_above', '')
    expr_str = expr_repr.get('expr', '')
    lines_below_str = expr_repr.get('lines_below', '')
    
    # Process lines_above
    above = textwrap.dedent(lines_above_str).splitlines() if lines_above_str else []
    # Process expr
    expr = expr_str.splitlines() if expr_str else []
    # Process lines_below
    below = textwrap.dedent(lines_below_str).splitlines() if lines_below_str else []
    
    # Add context lines
    parts.extend(f"│  {line}" for line in above)
    
    # Add expression lines
    if expr:
        parts.append(f">  {expr[0]}")
        parts.extend(f">  {line}" for line in expr[1:])
    
    parts.extend(f"│  {line}" for line in below)
    
    # Add resolved args (where clause)
    resolved_args = expr_repr.get('resolved_args', {})
    if resolved_args:
        parts.append("╰─ where:")
        for name, value in resolved_args.items():
            # Normalize whitespace in name
            name_oneline = " ".join(name.split())
            name_oneline = re.sub(r"\s+([)\]}.,])", r"\1", name_oneline)
            name_oneline = re.sub(r"([(\[{])\s+", r"\1", name_oneline)
            name_oneline = re.sub(r"\s*\.\s*", ".", name_oneline)
            
            # Normalize whitespace in value
            value_oneline = " ".join(value.split())
            
            parts.append(f"     {name_oneline} = {value_oneline}")
    
    return "\n".join(parts)


def get_timestamp():
    """Get current timestamp"""
    from datetime import datetime
    return datetime.now().isoformat()


def load_trace(trace_id, db_path='.merit/merit.db'):
    """Load trace spans from Merit database for given trace_id"""
    if not Path(db_path).exists():
        return []
    
    # Handle both formats: with and without 0x prefix
    trace_id_with_prefix = f"0x{trace_id}" if not trace_id.startswith('0x') else trace_id
    trace_id_without_prefix = trace_id.replace('0x', '')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query spans for this trace_id (try both formats)
        cursor.execute("""
            SELECT span_json 
            FROM trace_spans 
            WHERE trace_id IN (?, ?)
            ORDER BY start_time_ns
        """, (trace_id_with_prefix, trace_id_without_prefix))
        
        spans = []
        for (span_json,) in cursor.fetchall():
            try:
                span = json.loads(span_json)
                spans.append(span)
            except json.JSONDecodeError:
                continue
        
        conn.close()
        return spans
    except sqlite3.Error as e:
        print(f"Database error loading trace: {e}", file=sys.stderr)
        return []


def extract_sut_flow(spans):
    """Extract SUT execution flow (skip test infrastructure)"""
    flow = []
    for span in spans:
        name = span.get('name', '')
        # Skip test infrastructure
        if not name.startswith('test.') and not name.startswith('sut.'):
            flow.append(name)
    
    # Return last 10 components (most relevant)
    return flow[-10:] if len(flow) > 10 else flow


def extract_anomaly_flags(spans):
    """Extract behavioral anomaly flags from spans"""
    flags = {
        'has_validation_failure': False,
        'has_empty_response': False,
        'has_routing_decision': False,
        'has_retrieval': False,
        'has_tool_calls': False,
    }
    
    for span in spans:
        attrs = span.get('attributes', {})
        
        # Validation failure
        if attrs.get('validation_success') is False:
            flags['has_validation_failure'] = True
        
        # Empty/short response
        if 'gen_ai.completion.0.content' in attrs:
            content = attrs['gen_ai.completion.0.content']
            if not content or len(content) < 50:
                flags['has_empty_response'] = True
        
        # Routing decision
        if 'route.needs_tools' in attrs or 'route.needs_retrieval' in attrs:
            flags['has_routing_decision'] = True
        
        # Retrieval
        if 'retrieval.num_results' in attrs:
            flags['has_retrieval'] = True
        
        # Tool calls
        if span.get('name', '').startswith('travelops.tool.'):
            flags['has_tool_calls'] = True
    
    return flags


def extract_actual_output(spans):
    """
    Extract the actual SUT output from traces.
    
    This is what the system actually returned (for fix generation).
    """
    output = {}
    
    for span in spans:
        attrs = span.get('attributes', {})
        name = span.get('name', '')
        
        # Get final LLM response
        if 'gen_ai.completion.0.content' in attrs:
            output['llm_response'] = attrs['gen_ai.completion.0.content']
        
        # Get tool results
        if name.startswith('travelops.tool.'):
            tool_name = name.replace('travelops.tool.', '')
            if 'tool.result' in attrs:
                if 'tool_results' not in output:
                    output['tool_results'] = {}
                output['tool_results'][tool_name] = attrs['tool.result']
        
        # Get final agent output (if structured)
        if name == 'travelops.agent.run':
            if 'output.itinerary' in attrs:
                output['itinerary'] = attrs['output.itinerary']
            if 'output.message' in attrs:
                output['message'] = attrs['output.message']
    
    return output if output else None


def extract_input_data(spans):
    """
    Extract input data from traces (since Merit doesn't store it in DB).
    
    Returns the inputs that were passed to the SUT.
    """
    inputs = {}
    messages = {}  # Temp dict to collect messages by index
    
    for span in spans:
        attrs = span.get('attributes', {})
        name = span.get('name', '')
        
        # Get LLM prompts (multi-message format: prompt.0.content, prompt.1.content, etc.)
        for key, value in attrs.items():
            if key.startswith('gen_ai.prompt.') and key.endswith('.content'):
                # Extract index from key (e.g., "gen_ai.prompt.0.content" -> 0)
                try:
                    idx = int(key.split('.')[2])
                    role_key = f'gen_ai.prompt.{idx}.role'
                    role = attrs.get(role_key, 'unknown')
                    messages[idx] = {
                        'role': role,
                        'content': value
                    }
                except (ValueError, IndexError):
                    pass
        
        # Get system message
        if 'gen_ai.system' in attrs:
            inputs['system_message'] = attrs['gen_ai.system']
        
        # Get routing decisions (shows what the system decided to do)
        if 'route.needs_retrieval' in attrs:
            inputs['needs_retrieval'] = attrs['route.needs_retrieval']
        if 'route.needs_tools' in attrs:
            inputs['needs_tools'] = attrs['route.needs_tools']
        if 'route.tools' in attrs:
            inputs['tools_selected'] = attrs['route.tools']
        
        # Get tool inputs
        if name.startswith('travelops.tool.'):
            tool_name = name.replace('travelops.tool.', '')
            if 'tool.input' in attrs:
                if 'tool_inputs' not in inputs:
                    inputs['tool_inputs'] = {}
                inputs['tool_inputs'][tool_name] = attrs['tool.input']
        
        # Get agent input
        if name == 'travelops.agent.run':
            if 'input.query' in attrs:
                inputs['query'] = attrs['input.query']
            if 'input.user_message' in attrs:
                inputs['user_message'] = attrs['input.user_message']
    
    # Convert messages dict to sorted list
    if messages:
        inputs['messages'] = [messages[i] for i in sorted(messages.keys())]
    
    return inputs if inputs else None


def extract_code_locations(spans):
    """
    Extract code locations from execution spans for fix generation.
    
    Returns file paths and line numbers where code was executed.
    """
    locations = []
    seen = set()
    
    for span in spans:
        attrs = span.get('attributes', {})
        name = span.get('name', '')
        
        # Skip test infrastructure
        if name.startswith('test.') or name.startswith('sut.'):
            continue
        
        # Extract code location if available
        code_filepath = attrs.get('code.filepath')
        code_lineno = attrs.get('code.lineno')
        code_function = attrs.get('code.function')
        
        if code_filepath or name:
            # Use name as fallback for function
            function = code_function or name
            
            # Create unique key
            key = f"{code_filepath or name}:{code_lineno or 0}:{function}"
            if key not in seen:
                seen.add(key)
                locations.append({
                    'component': name,
                    'filepath': code_filepath,
                    'lineno': code_lineno,
                    'function': function
                })
    
    return locations


def extract_failure_signature(case_id, db_path='.merit/merit.db'):
    """
    Extract failure signature for clustering and fix generation.
    
    Queries Merit database for test execution details and trace spans.
    
    Args:
        case_id: Test case UUID
        db_path: Path to Merit database (default: .merit/merit.db)
    
    Returns:
        Unified signature with clustering and fix_context sections
    """
    
    # Get case info
    case_info = get_case_info(case_id, db_path)
    if not case_info:
        return None
    
    # Get error message from case info
    error_message = case_info.get('error_message') or "Unknown error"
    
    # Get all assertions in pretty format for clustering key
    all_assertions_pretty = case_info.get('all_assertions_pretty', [])
    
    # Create cluster key: concatenate all assertion pretty strings
    # This gives consistent, readable representation for embedding
    cluster_key = "\n\n".join(all_assertions_pretty) if all_assertions_pretty else ""
    
    # Load and analyze trace from database
    trace_id = case_info['trace_id']
    spans = []
    if trace_id:
        spans = load_trace(trace_id, db_path)
    
    # Extract data for fix generation (from traces, not DB)
    input_data = extract_input_data(spans)
    actual_output = extract_actual_output(spans)
    code_locations = extract_code_locations(spans)
    
    # Create unified signature (clustering + fix generation)
    signature = {
        # === METADATA ===
        'case_id': case_id,
        'timestamp': get_timestamp(),
        'test_name': case_info['test_name'],
        'test_module': case_info['test_module'],
        
        # === CLUSTERING DATA ===
        # ONLY the cluster_key (concatenated pretty assertions)
        'cluster_key': cluster_key,
        
        # === FIX GENERATION DATA ===
        'fix_context': {
            # All assertions with full context (passed AND failed)
            'assertions': case_info.get('all_assertions_pretty', []),
            
            # Test context
            'test_file': case_info['test_module'],
            
            # Execution path through SUT components
            'execution_flow': [loc['component'] for loc in code_locations] if code_locations else [],
            
            # What the system received
            'input': input_data,
            
            # What the system produced
            'output': actual_output
        }
    }
    
    return signature


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/extract_failure_signature.py <case_id> [db_path]", file=sys.stderr)
        print("  db_path defaults to .merit/merit.db", file=sys.stderr)
        sys.exit(1)
    
    case_id = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else '.merit/merit.db'
    
    signature = extract_failure_signature(case_id, db_path)
    
    if signature:
        print(json.dumps(signature, indent=2))
    else:
        print(f"Error: Could not extract signature for case {case_id}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
