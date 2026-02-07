#!/usr/bin/env python3
"""
Generate an HTML report for a failed test case showing all trace data.

Usage:
    python scripts/view_trace.py <case_id> [trace_file]
    
Example:
    python scripts/view_trace.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1
    python scripts/view_trace.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1 traces/traces-contract-faults.jsonl
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


def get_test_metadata(case_id: str, db_path: Path) -> Optional[Dict[str, Any]]:
    """Query Merit database for test execution metadata."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            te.execution_id,
            te.test_name,
            te.case_id,
            te.trace_id,
            te.status,
            te.duration_ms,
            te.error_message,
            r.start_time as created_at
        FROM test_executions te
        JOIN runs r ON te.run_id = r.run_id
        WHERE te.case_id = ?
        ORDER BY r.start_time DESC
        LIMIT 1
    """, (case_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return dict(row)


def load_trace_spans(trace_id: str, trace_file: Path) -> List[Dict[str, Any]]:
    """Load all spans for a given trace_id from JSONL file."""
    spans = []
    trace_id_hex = trace_id if trace_id.startswith("0x") else f"0x{trace_id}"
    
    with open(trace_file, 'r') as f:
        for line in f:
            span = json.loads(line)
            if span.get('context', {}).get('trace_id') == trace_id_hex:
                spans.append(span)
    
    # Sort by start_time
    spans.sort(key=lambda s: s.get('start_time', ''))
    return spans


def build_span_hierarchy(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build a hierarchical structure of spans based on parent_id."""
    span_map = {s['context']['span_id']: s for s in spans}
    roots = []
    
    for span in spans:
        parent_id = span['context'].get('parent_id')
        if parent_id and parent_id in span_map:
            parent = span_map[parent_id]
            if 'children' not in parent:
                parent['children'] = []
            parent['children'].append(span)
        else:
            roots.append(span)
    
    return roots


def calculate_duration_ms(span: Dict[str, Any]) -> float:
    """Calculate span duration in milliseconds."""
    start = datetime.fromisoformat(span['start_time'].replace('Z', '+00:00'))
    end = datetime.fromisoformat(span['end_time'].replace('Z', '+00:00'))
    return (end - start).total_seconds() * 1000


def extract_clustering_features(span: Dict[str, Any]) -> Dict[str, Any]:
    """Extract attributes useful for clustering similar failures."""
    attrs = span.get('attributes', {})
    
    features = {
        'span_name': span['name'],
        'span_kind': span.get('kind'),
        'status_code': span.get('status', {}).get('status_code'),
        'error_type': span.get('status', {}).get('description', '').split(':')[0] if span.get('status', {}).get('status_code') == 'ERROR' else None,
    }
    
    # LLM-related features
    if 'gen_ai.request.model' in attrs:
        features.update({
            'llm_model': attrs.get('gen_ai.request.model'),
            'llm_temperature': attrs.get('gen_ai.request.temperature'),
            'llm_tokens': attrs.get('llm.usage.total_tokens'),
            'llm_prompt_tokens': attrs.get('llm.usage.prompt_tokens'),
            'llm_completion_tokens': attrs.get('llm.usage.completion_tokens'),
        })
    
    # Tool/function call features
    if 'tool.name' in attrs:
        features['tool_name'] = attrs.get('tool.name')
    
    # Route features
    if 'route.name' in attrs:
        features['route_name'] = attrs.get('route.name')
    
    # Error features
    if 'exception.type' in attrs:
        features.update({
            'exception_type': attrs.get('exception.type'),
            'exception_message': attrs.get('exception.message', '')[:200],  # Truncate long messages
        })
    
    # Session features
    if 'session.id' in attrs:
        features['session_id'] = attrs.get('session.id')
    
    return {k: v for k, v in features.items() if v is not None}


def generate_html_report(case_id: str, metadata: Dict[str, Any], spans: List[Dict[str, Any]], output_file: Path):
    """Generate HTML report with all trace data."""
    
    hierarchy = build_span_hierarchy(spans)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Trace Report: {case_id[:8]}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #666;
            margin-top: 20px;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #e74c3c;
        }}
        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}
        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}
        .metadata-label {{
            font-weight: bold;
            color: #666;
            font-size: 0.85em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .metadata-value {{
            color: #333;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.95em;
        }}
        .status-failed {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .status-passed {{
            color: #27ae60;
            font-weight: bold;
        }}
        .span {{
            margin: 10px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #fafafa;
        }}
        .span-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .span-name {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .span-duration {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .span-attributes {{
            background: white;
            padding: 10px;
            border-radius: 3px;
            margin-top: 10px;
            max-height: 400px;
            overflow-y: auto;
        }}
        .attribute {{
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 15px;
            padding: 8px 0;
            border-bottom: 1px solid #ecf0f1;
        }}
        .attribute:last-child {{
            border-bottom: none;
        }}
        .attr-key {{
            font-weight: 600;
            color: #34495e;
            word-break: break-word;
        }}
        .attr-value {{
            color: #555;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .children {{
            margin-left: 30px;
            margin-top: 15px;
            border-left: 3px solid #3498db;
            padding-left: 15px;
        }}
        .clustering-features {{
            background: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-top: 10px;
            border-left: 4px solid #3498db;
        }}
        .feature-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        .feature-item {{
            background: white;
            padding: 8px;
            border-radius: 3px;
        }}
        .feature-label {{
            font-size: 0.8em;
            color: #666;
            text-transform: uppercase;
        }}
        .feature-value {{
            font-weight: bold;
            color: #2c3e50;
            margin-top: 3px;
        }}
        .error-box {{
            background: #fee;
            border: 1px solid #e74c3c;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .error-title {{
            font-weight: bold;
            color: #c0392b;
            margin-bottom: 10px;
        }}
        .error-content {{
            font-family: 'Monaco', 'Courier New', monospace;
            white-space: pre-wrap;
            color: #555;
            font-size: 0.9em;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .llm-call {{
            border-left: 4px solid #9b59b6;
        }}
        .tool-call {{
            border-left: 4px solid #f39c12;
        }}
        .error-span {{
            border-left: 4px solid #e74c3c;
            background: #fee;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .json-preview {{
            max-height: 200px;
            overflow-y: auto;
            background: #2c3e50;
            color: #ecf0f1;
            padding: 10px;
            border-radius: 5px;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Trace Report</h1>
        
        <div class="metadata">
            <h3>Test Execution Metadata</h3>
            <div class="metadata-grid">
                <div class="metadata-item">
                    <span class="metadata-label">Test Name</span>
                    <span class="metadata-value">{metadata['test_name']}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Case ID</span>
                    <span class="metadata-value">{metadata['case_id']}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Trace ID</span>
                    <span class="metadata-value">{metadata['trace_id']}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Status</span>
                    <span class="metadata-value status-{metadata['status']}">{metadata['status'].upper()}</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Duration</span>
                    <span class="metadata-value">{metadata['duration_ms']:.2f} ms</span>
                </div>
                <div class="metadata-item">
                    <span class="metadata-label">Timestamp</span>
                    <span class="metadata-value">{metadata['created_at']}</span>
                </div>
            </div>
        </div>
"""
    
    # Add error message if present
    if metadata.get('error_message'):
        html += f"""
        <div class="error-box">
            <div class="error-title">Error Message:</div>
            <div class="error-content">{metadata['error_message']}</div>
        </div>
"""
    
    # Summary statistics
    total_spans = len(spans)
    llm_spans = sum(1 for s in spans if 'gen_ai.request.model' in s.get('attributes', {}))
    tool_spans = sum(1 for s in spans if 'tool.name' in s.get('attributes', {}))
    error_spans = sum(1 for s in spans if s.get('status', {}).get('status_code') == 'ERROR')
    total_duration = sum(calculate_duration_ms(s) for s in spans)
    
    html += f"""
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-value">{total_spans}</div>
                <div class="stat-label">Total Spans</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{llm_spans}</div>
                <div class="stat-label">LLM Calls</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{tool_spans}</div>
                <div class="stat-label">Tool Calls</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{error_spans}</div>
                <div class="stat-label">Errors</div>
            </div>
        </div>
        
        <h2>📊 Clustering Features</h2>
        <p>These features can be used to cluster similar failures together:</p>
"""
    
    # Render clustering features for all spans
    for span in spans:
        features = extract_clustering_features(span)
        if features:
            html += f"""
        <div class="clustering-features">
            <strong>{span['name']}</strong>
            <div class="feature-grid">
"""
            for key, value in features.items():
                html += f"""
                <div class="feature-item">
                    <div class="feature-label">{key}</div>
                    <div class="feature-value">{value}</div>
                </div>
"""
            html += """
            </div>
        </div>
"""
    
    html += """
        <h2>🌲 Span Hierarchy</h2>
        <p>Full execution trace with all attributes:</p>
"""
    
    def render_span(span: Dict[str, Any], level: int = 0) -> str:
        duration = calculate_duration_ms(span)
        attrs = span.get('attributes', {})
        
        # Determine span type for styling
        span_class = "span"
        if 'gen_ai.request.model' in attrs:
            span_class += " llm-call"
        elif 'tool.name' in attrs:
            span_class += " tool-call"
        if span.get('status', {}).get('status_code') == 'ERROR':
            span_class += " error-span"
        
        html = f"""
        <div class="{span_class}">
            <div class="span-header">
                <span class="span-name">{span['name']}</span>
                <span class="span-duration">{duration:.2f} ms</span>
            </div>
"""
        
        # Show key attributes
        if attrs:
            html += """
            <div class="span-attributes">
"""
            # Sort attributes for better readability
            important_attrs = [
                'gen_ai.request.model',
                'gen_ai.request.temperature',
                'gen_ai.prompt.1.content',
                'gen_ai.completion.0.content',
                'llm.usage.total_tokens',
                'tool.name',
                'route.name',
                'exception.type',
                'exception.message',
            ]
            
            # Show important attributes first
            for key in important_attrs:
                if key in attrs:
                    value = attrs[key]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 500:
                        value = value[:500] + "... (truncated)"
                    html += f"""
                <div class="attribute">
                    <div class="attr-key">{key}</div>
                    <div class="attr-value">{value}</div>
                </div>
"""
            
            # Show remaining attributes
            for key, value in sorted(attrs.items()):
                if key not in important_attrs:
                    if isinstance(value, str) and len(value) > 500:
                        value = value[:500] + "... (truncated)"
                    html += f"""
                <div class="attribute">
                    <div class="attr-key">{key}</div>
                    <div class="attr-value">{value}</div>
                </div>
"""
            
            html += """
            </div>
"""
        
        # Render children
        if 'children' in span:
            html += """
            <div class="children">
"""
            for child in span['children']:
                html += render_span(child, level + 1)
            html += """
            </div>
"""
        
        html += """
        </div>
"""
        return html
    
    for root in hierarchy:
        html += render_span(root)
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/view_trace.py <case_id> [trace_file]")
        print("\nExample:")
        print("  python scripts/view_trace.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1")
        sys.exit(1)
    
    case_id = sys.argv[1]
    
    # Determine trace file
    if len(sys.argv) >= 3:
        trace_file = Path(sys.argv[2])
    else:
        # Try to find the most recent trace file
        traces_dir = Path('traces')
        if traces_dir.exists():
            trace_files = list(traces_dir.glob('*.jsonl'))
            if trace_files:
                trace_file = max(trace_files, key=lambda p: p.stat().st_mtime)
                print(f"Using most recent trace file: {trace_file}")
            else:
                print("Error: No trace files found in traces/ directory")
                sys.exit(1)
        else:
            print("Error: traces/ directory not found")
            sys.exit(1)
    
    # Query database
    db_path = Path('.merit/merit.db')
    if not db_path.exists():
        print(f"Error: Merit database not found at {db_path}")
        sys.exit(1)
    
    print(f"Querying database for case_id: {case_id}")
    metadata = get_test_metadata(case_id, db_path)
    
    if not metadata:
        print(f"Error: No test execution found for case_id: {case_id}")
        sys.exit(1)
    
    print(f"Found test: {metadata['test_name']} (status: {metadata['status']})")
    print(f"Trace ID: {metadata['trace_id']}")
    
    if not metadata['trace_id']:
        print(f"\nError: No trace_id found for this test execution.")
        print(f"This test was likely run without the --trace flag.")
        print(f"Run tests with tracing enabled:")
        print(f"  merit test --trace --trace-output traces/traces.jsonl")
        sys.exit(1)
    
    # Load trace spans
    print(f"Loading trace spans from: {trace_file}")
    spans = load_trace_spans(metadata['trace_id'], trace_file)
    
    if not spans:
        print(f"Warning: No trace spans found for trace_id: {metadata['trace_id']}")
        print("The trace file may not contain data for this test execution.")
        sys.exit(1)
    
    print(f"Found {len(spans)} spans")
    
    # Generate HTML report
    reports_dir = Path('trace_reports')
    reports_dir.mkdir(exist_ok=True)
    
    output_file = reports_dir / f"trace_report_{case_id[:8]}.html"
    print(f"Generating HTML report: {output_file}")
    generate_html_report(case_id, metadata, spans, output_file)
    
    print(f"\n✅ Report generated successfully!")
    print(f"📄 Open in browser: file://{output_file.absolute()}")


if __name__ == '__main__':
    main()
