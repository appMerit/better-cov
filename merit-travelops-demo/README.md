# TravelOps Merit Demo Repository

This repository demonstrates Merit testing with fix-oriented failure clustering using a TravelOps Assistant system.

## Overview

The TravelOps Assistant is a text-based AI system that helps users plan trips. This demo includes:

- **System Under Test (SUT)**: A realistic travel planning assistant with routing, retrieval, tools, and state management
- **10 Fault Profiles**: Each generating 20-30 repeatable failures clustered by fix type
- **Merit Test Suite**: 300+ test cases organized into 10 clusters
- **Fault Injection System**: Test-only fault injection that doesn't require app code changes

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### Run Baseline (No Faults)

```bash
MERIT_FAULT_PROFILE=none uv run merit test
```

Most tests should pass in baseline mode.

## Basic Usage: With or Without Faults

Each test can run in **two modes**:

**1. Baseline (no faults)** - Expected to pass or have minimal failures:
```bash
MERIT_FAULT_PROFILE=none uv run merit test tests/merit_travelops_contract.py
```

**2. Fault-injected** - Expected to have MORE failures:
```bash
MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py
```

The `MERIT_FAULT_PROFILE` environment variable controls fault injection:
- `none` = Baseline mode (no bugs injected)
- `<fault_name>` = Inject specific bug pattern

### Run with Fault Profile

To generate failures for a specific cluster, run the corresponding test file with a fault profile:

```bash
# Cluster 1: Contract/JSON schema failures (30 failures expected)
MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py

# Enable OpenTelemetry tracing to capture spans
MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py --trace

# Custom trace output file
MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py --trace --trace-output traces-contract.jsonl

# Cluster 2: Prompt assembly failures
MERIT_FAULT_PROFILE=prompt_role_mix uv run merit test tests/merit_travelops_prompting.py

# Cluster 3: Retrieval relevance failures
MERIT_FAULT_PROFILE=retrieval_irrelevant uv run merit test tests/merit_travelops_retrieval.py

# Cluster 4: Grounding enforcement failures
MERIT_FAULT_PROFILE=grounding_bypass uv run merit test tests/merit_travelops_grounding.py

# Cluster 5: Tool routing failures
MERIT_FAULT_PROFILE=router_wrong_tool uv run merit test tests/merit_travelops_routing.py

# Cluster 6: Tool argument failures
MERIT_FAULT_PROFILE=tool_args_corrupt uv run merit test tests/merit_travelops_tool_args.py

# Cluster 7: Memory/state failures
MERIT_FAULT_PROFILE=memory_disabled uv run merit test tests/merit_travelops_state.py

# Cluster 8: Control flow failures
MERIT_FAULT_PROFILE=loop_termination_bug uv run merit test tests/merit_travelops_control_flow.py

# Cluster 9: Determinism failures
MERIT_FAULT_PROFILE=nondeterministic_config uv run merit test tests/merit_travelops_determinism.py

# Cluster 10: Postprocessing failures
MERIT_FAULT_PROFILE=postprocess_mapping_bug uv run merit test tests/merit_travelops_postprocess.py
```

### Quick Test with Stub LLM (Fast)

For rapid testing without API calls (~15ms instead of ~60 seconds):

```bash
# Test baseline with stub LLM (all pass)
TRAVELOPS_LLM_PROVIDER=stub MERIT_FAULT_PROFILE=none uv run merit test tests/merit_travelops_contract.py

# Test with fault (all fail) - completes in milliseconds
TRAVELOPS_LLM_PROVIDER=stub MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py
```

### Run All Tests (With or Without Faults)

Use one script to run all 10 tests in either mode:

```bash
# Run all tests WITHOUT faults (baseline - fast, no traces)
./scripts/run_all_faults.sh baseline

# Run all tests WITH faults (fast, no traces)
./scripts/run_all_faults.sh faults

# Enable OpenTelemetry tracing (add 'traces' argument)
./scripts/run_all_faults.sh baseline traces  # Baseline with traces
./scripts/run_all_faults.sh faults traces    # Faults with traces
```

**What it does:**
- **Baseline mode**: Runs each test with `MERIT_FAULT_PROFILE=none` (no bugs injected)
- **Faults mode**: Runs each test with its associated fault profile:
  - `merit_travelops_contract.py` → `contract_json` fault
  - `merit_travelops_prompting.py` → `prompt_role_mix` fault
  - `merit_travelops_retrieval.py` → `retrieval_irrelevant` fault
  - ... and so on for all 10 clusters

**Tracing (optional):**
- **Without `traces` arg**: Fast execution, no trace files generated
- **With `traces` arg**: Slower but generates detailed trace files in `traces/` directory:
  - `traces/traces-{tag}-baseline.jsonl` (baseline mode)
  - `traces/traces-{tag}-faults.jsonl` (faults mode)
  
Trace files include:
- LLM calls with tokens, latency, and full request/response
- Tool calls and arguments
- Retrieval operations
- Agent execution flow

**Note**: The `traces/` directory contains `.gitkeep` but trace files (`*.jsonl`) are gitignored. Traces are generated locally when you run tests.

## Expected Failure Counts

Each fault profile should generate approximately 20-30 failures:

| Cluster | Fault Profile | Tag | Expected Failures | Fix Target |
|---------|--------------|-----|-------------------|------------|
| 1 | `contract_json` | `contract` | ~30 | `app/postprocess.py`, `app/schemas.py` |
| 2 | `prompt_role_mix` | `prompting` | ~30 | `app/prompting.py` |
| 3 | `retrieval_irrelevant` | `retrieval` | ~30 | `app/retrieval.py` |
| 4 | `grounding_bypass` | `grounding` | ~30 | `app/prompting.py` |
| 5 | `router_wrong_tool` | `routing` | ~30 | `app/router.py` |
| 6 | `tool_args_corrupt` | `tool_args` | ~30 | `app/tools/*.py` |
| 7 | `memory_disabled` | `memory` | ~30 | `app/state.py` |
| 8 | `loop_termination_bug` | `control_flow` | ~30 | `app/agent.py` |
| 9 | `nondeterministic_config` | `determinism` | ~30 | `app/config.py` |
| 10 | `postprocess_mapping_bug` | `postprocess` | ~30 | `app/postprocess.py` |

## OpenTelemetry Traces

Merit automatically captures OpenTelemetry spans when you use the `--trace` flag. The traces include:

- **LLM calls** - Model, tokens, latency, request/response content
- **Tool calls** - Which tools were invoked and their arguments
- **Retrieval operations** - KB queries and retrieved documents
- **Agent steps** - Full execution flow with timing
- **Custom spans** - From `@trace_operation` decorators in the app

### Viewing Traces

Traces are written to `traces.jsonl` (JSONL format - one JSON object per line):

```bash
# Run with tracing enabled
MERIT_FAULT_PROFILE=contract_json uv run merit test tests/merit_travelops_contract.py --trace

# View traces
cat traces.jsonl | jq '.'

# Filter to LLM calls only
cat traces.jsonl | jq 'select(.attributes."llm.model" != null)'

# See what tools were called
cat traces.jsonl | jq 'select(.name | contains("tool"))'
```

### Using Traces in Tests

You can assert on traces in your test functions using `trace_context`:

```python
def merit_test(travelops_agent, trace_context):
    response = travelops_agent.run("Book a flight to Paris")
    
    # Get all spans from the SUT
    spans = trace_context.get_sut_spans(travelops_agent)
    
    # Assert tool was called
    tool_calls = [s for s in spans if "tool" in s.name.lower()]
    assert len(tool_calls) > 0, "Expected tool call"
```

## Failure Analysis & Clustering

### Complete Collection: Run All Tests + Extract All Failures

**One-command solution** to run all tests with faults and collect all failure signatures in one file:

```bash
# Run all tests with all faults, capture traces, extract signatures
./scripts/collect_all_failures.sh
```

**What it does:**
1. Runs all 10 test suites with their respective fault profiles
2. Captures OpenTelemetry traces for all executions
3. Extracts failure signatures for all failed test cases
4. Produces a single timestamped JSON file: `trace_reports/failure_signature_collection_YYYYMMDD_HHMMSS.json`

**Output structure:**
```json
[
  {
    "case_id": "d3a2188d-...",
    "timestamp": "2026-01-23...",
    "error_signature": {...},
    "execution_signature": {...},
    "system_behavior_signature": {...},
    "test_context": {...},
    "clustering_features": {...},
    "embedding_text": {...}
  },
  {
    "case_id": "abc123-...",
    ...
  }
]
```

**Typical runtime:** 5-10 minutes (runs 300+ test cases with real LLM calls)

**View and cluster results:**
```bash
# Count total signatures
cat trace_reports/failure_signature_collection_*.json | jq 'length'

# View first signature
cat trace_reports/failure_signature_collection_*.json | jq '.[0]'

# Cluster failures by root cause (pattern-based)
python3 scripts/cluster_failures.py trace_reports/failure_signature_collection_*.json
```

**Expected clustering:** ~10-15 clusters representing distinct root causes.

---

### Clustering Failures by Root Cause

After collecting failure signatures, cluster them using semantic similarity with HDBSCAN:

```bash
# Auto-discover cluster count (default min_cluster_size=5)
python3 scripts/cluster_failures.py trace_reports/failure_signature_collection_*.json

# Or adjust minimum cluster size
python3 scripts/cluster_failures.py trace_reports/failure_signature_collection_*.json 10
```

**Requirements:**
- `OPENAI_API_KEY` in your `.env` file
- Python packages: `openai`, `hdbscan`, `scikit-learn`, `numpy`, `python-dotenv`

**How it works:**
1. Creates embedding text from each failure (error + execution path + anomalies + test type)
2. Gets embeddings from OpenAI API (`text-embedding-3-small`)
3. Clusters using **HDBSCAN** - automatically discovers optimal cluster count
4. Groups failures that are semantically similar

**Benefits:**
- ✅ **Auto-discovers clusters** - no need to know k upfront!
- ✅ No hard-coded rules - works for any assertion type
- ✅ Generalizable - handles semantic predicates, custom assertions, etc.
- ✅ Quality metrics - silhouette score indicates cluster quality
- ✅ Handles noise - identifies outliers that don't fit any cluster

**Output:**
- Detailed cluster analysis printed to console
- Cluster assignments saved to `*_clusters.json`
- ~90% coherent clusters (≤3 error types per cluster)

**Expected output:** ~10 clusters for this test suite (one per fault profile).

---

### Individual Failure Extraction

For ad-hoc extraction or debugging individual failures:

```bash
# Extract signature for a single failed test
python3 scripts/extract_failure_signature.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1
```

**Extracts (works for ANY system - LLM, web API, database, etc.):**
- ✅ Error signatures (error type, patterns, exception types)
- ✅ Execution signatures (which components failed, execution flow)
- ✅ System behavior signatures (auto-detects: LLM, HTTP, DB, or generic)
- ✅ Pre-computed clustering features (primary_key, anomaly flags)
- ✅ Embedding text (for semantic clustering)

### Viewing Trace Details

For debugging and understanding individual failures, use the `view_trace.py` script to generate a comprehensive HTML report for any test case:

```bash
# Generate HTML report for a specific test case
python3 scripts/view_trace.py <case_id>

# Example with the case_id from a failed test
python3 scripts/view_trace.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1

# Specify which trace file to use (defaults to most recent)
python3 scripts/view_trace.py d3a2188d-75f8-46bd-8c55-0868cf9da1e1 traces/traces-contract-faults.jsonl
```

**What the script does:**
1. Queries the Merit database (`.merit/merit.db`) to find the trace_id for the given case_id
2. Extracts all trace spans from the JSONL trace file
3. Generates a comprehensive HTML report in `trace_reports/` directory showing:
   - Test execution metadata (status, duration, error message)
   - Summary statistics (total spans, LLM calls, tool calls, errors)
   - **Clustering features** - Extracted attributes useful for grouping similar failures:
     - Span names and types
     - LLM models, temperature, token usage
     - Tool names and routes
     - Exception types and error patterns
     - Session IDs
   - Full span hierarchy with all attributes
   - LLM prompts and completions
   - Timing information

**Output:**
- HTML file: `trace_reports/trace_report_<case_id>.html`
- Open in browser to view the interactive report
- The "Clustering Features" section shows exactly what data is available for your clustering solution

**Workflow for clustering:**
1. Run tests with faults: `./scripts/run_all_faults.sh faults traces`
2. Get failed test case_ids from test output or database
3. Generate trace reports for each failed case
4. Use the clustering features to group similar failures
5. Map failure clusters back to code locations using the trace patterns

**Example query to find failed test cases:**
```bash
# Get all failed test case_ids from most recent run
sqlite3 .merit/merit.db "SELECT case_id, test_name, error_message FROM test_executions WHERE status = 'failed' ORDER BY case_id LIMIT 10;"
```

## Architecture

### Application Structure (`app/`)

```
app/
├── agent.py           # Main orchestration logic
├── config.py          # Configuration management
├── llm_client.py      # LLM abstraction (stub + OpenAI)
├── prompting.py       # Message building
├── router.py          # Request routing
├── retrieval.py       # Knowledge base retrieval
├── state.py           # Session memory
├── postprocess.py     # Output normalization
├── schemas.py         # Data schemas
├── tracing.py         # OpenTelemetry helpers
└── tools/
    ├── weather.py     # Weather tool
    ├── hotels.py      # Hotel search
    ├── flights.py     # Flight search
    └── web_search.py  # Web search stub
```

### Test Structure (`tests/`)

```
tests/
├── faults/
│   ├── profiles.py    # Fault profile definitions
│   └── patchers.py    # Fault injection logic
├── fixtures/
│   ├── kb_docs.py     # Knowledge base fixtures
│   ├── scenarios.py   # Test case generators
│   └── expected_schemas.py  # Validation helpers
├── merit_travelops_contract.py      # Cluster 1 tests
├── merit_travelops_prompting.py     # Cluster 2 tests
├── merit_travelops_retrieval.py     # Cluster 3 tests
├── merit_travelops_grounding.py     # Cluster 4 tests
├── merit_travelops_routing.py       # Cluster 5 tests
├── merit_travelops_tool_args.py     # Cluster 6 tests
├── merit_travelops_state.py         # Cluster 7 tests
├── merit_travelops_control_flow.py  # Cluster 8 tests
├── merit_travelops_determinism.py   # Cluster 9 tests
└── merit_travelops_postprocess.py   # Cluster 10 tests
```

## Configuration

### Environment Variables

You can set these via command line or in a `.env` file (see `.env.example`):

- `MERIT_FAULT_PROFILE`: Which fault to inject (default: `none`)
  - Options: `none`, `contract_json`, `prompt_role_mix`, `retrieval_irrelevant`, `grounding_bypass`, `router_wrong_tool`, `tool_args_corrupt`, `memory_disabled`, `loop_termination_bug`, `nondeterministic_config`, `postprocess_mapping_bug`
- `TRAVELOPS_LLM_PROVIDER`: `stub` or `openai` (default: `stub`)
- `TRAVELOPS_TEMPERATURE`: LLM temperature (default: `0.0`)
- `TRAVELOPS_MAX_STEPS`: Max agent steps (default: `5`)
- `OPENAI_API_KEY`: OpenAI API key (optional, for OpenAI mode)
- `MERIT_API_KEY`: Merit API key (optional, for semantic predicates)

### Modes

#### Stub Mode (Default)

Deterministic mode that doesn't require API keys. Perfect for CI and reproducible testing.

```bash
TRAVELOPS_LLM_PROVIDER=stub uv run merit test
```

#### OpenAI Mode (Optional)

For more realistic text generation (requires OpenAI API key):

```bash
TRAVELOPS_LLM_PROVIDER=openai uv run merit test
```

Or create a `.env` file:
```bash
TRAVELOPS_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
MERIT_API_KEY=your-merit-key  # Optional
```

**Performance:** With OpenAI, each test profile takes ~60 seconds (30 tests × 2 sec/test). With stub LLM, it's <15ms.

## Merit Framework Usage

This demo uses Merit to its fullest extent with all key features:

### ✅ `@sut` Decorator (System Under Test)

All test modules use a class-based `@sut` decorator to mark the TravelOps agent as the system under test. This enables:
- **Automatic tracing** of all SUT calls
- **Better Merit reports** with SUT-specific quality metrics  
- **Access to trace spans** for debugging

**Pattern:**
```python
@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)

@iter_cases(generate_contract_cases())
def merit_contract_json_schema(case: Case, travel_ops_sut):
    response = travel_ops_sut(**case.sut_input_values)
    # ... assertions ...
```

### ✅ `@iter_cases` (Dataset-Driven Testing)

All tests iterate over 30 cases per fault cluster using `@iter_cases`:

```python
@iter_cases(generate_contract_cases())
def merit_contract_json_schema(case: Case, travel_ops_sut):
    response = travel_ops_sut(**case.sut_input_values)
    # Access references for validation
    required_fields = case.references.get("required_fields", [])
```

**Benefits:**
- Type-safe access to inputs and references
- Easy to load cases from external sources
- Individual results per case in reports
- Tagging and metadata for filtering

### ✅ Semantic Predicates (LLM-Powered Assertions)

Used in `retrieval` and `grounding` tests for meaning-based comparisons:

```python
from merit.predicates import has_facts, has_unsupported_facts

# Check if response contains required fact (semantic similarity)
result = await has_facts(response_text, required_fact, strict=False)
assert result, f"Missing fact. Confidence: {result.confidence}"

# Check for hallucinations (facts not in context)
has_hallucinations = await has_unsupported_facts(response_text, kb_context)
assert not has_hallucinations
```

**Why semantic predicates?**
- LLM outputs vary in phrasing but preserve meaning
- Exact string matching is too brittle
- Confidence scores and reasoning for debugging

### ✅ Case Metadata and References

Every test case includes structured data:

```python
Case(
    tags={"contract"},
    metadata={"scenario_id": "contract_1_basic", "variation": "basic"},
    sut_input_values={"prompt": "Plan a trip to Paris"},
    references={
        "required_fields": ["destination", "dates"],
        "expected_city": "Paris",
    },
)
```

### 📊 Test Coverage

| Module | @sut | @iter_cases | Semantic Predicates | Cases |
|--------|------|-------------|---------------------|-------|
| contract.py | ✅ | ✅ | - | 30 |
| prompting.py | ✅ | ✅ | - | 30 |
| retrieval.py | ✅ | ✅ | `has_facts` | 30 |
| grounding.py | ✅ | ✅ | `has_unsupported_facts` | 30 |
| routing.py | ✅ | ✅ | - | 30 |
| tool_args.py | ✅ | ✅ | - | 30 |
| state.py | ✅ | ✅ | - | 30 |
| control_flow.py | ✅ | ✅ | - | 30 |
| determinism.py | ✅ | ✅ | - | 30 |
| postprocess.py | ✅ | ✅ | - | 30 |

**Total:** 300 test cases across 10 failure clusters

## Fault Injection Design

All faults are injected at **test time only** using monkeypatching. The fault injection system:

- ✅ Wraps stable interfaces in `app/`
- ✅ Uses environment variables for activation
- ✅ Never modifies `app/` code
- ❌ Should NOT be "fixed" by disabling fault injection

### Patch Surface Policy

See `PATCH_SURFACE.yml` for the complete policy:

**Allowlist** (where fixes belong):
- `app/**`

**Denylist** (never modify to fix tests):
- `tests/**`
- `**/faults/**`
- `**/fixtures/**`

## Development

### Running Specific Tests

```bash
# Run one cluster
merit test tests/merit_travelops_contract.py

# Run with tag
merit test --tag contract

# Run with tracing
merit test --trace --trace-output traces.jsonl

# Filter by keyword
merit test -k "json_schema"
```

### Adding New Test Cases

1. Add scenarios to `tests/fixtures/scenarios.py`
2. Update the generator function for your cluster
3. Tests automatically pick up new cases via `@iter_cases()`

### Debugging Failures

```bash
# Run with verbose output
merit test -v

# Run single test case
merit test tests/merit_travelops_contract.py::merit_contract_json_schema[contract_0_basic]

# Examine traces
cat traces-contract.jsonl | jq .
```

## Design Principles

### 1. Fix-Oriented Clustering

Each fault profile targets a specific part of the application:

- **Contract failures** → Fix schema validation
- **Routing failures** → Fix router logic
- **Memory failures** → Fix state management

### 2. Realistic Failures

Faults simulate real bugs:

- Dropped fields (not null checks)
- Wrong tool selection (not tool crashes)
- Irrelevant docs (not retrieval crashes)

### 3. Deterministic by Default

Stub mode ensures:

- Same input → Same output
- No API dependencies
- Fast execution
- CI-friendly

### 4. Observable System

Every operation emits OpenTelemetry spans:

- Tool calls include arguments
- Retrievals include doc IDs
- LLM calls include provider/temp
- Assertions can check trace attributes

## Tracing

### Span Structure

```
travelops.agent.run
├── travelops.state.load
├── travelops.route
├── travelops.retrieval
│   └── (doc_ids, scores)
├── travelops.tool.call
│   └── (tool.name, tool.args)
├── travelops.prompt.build
│   └── (prompt_hash, message_count)
├── travelops.llm.generate
│   └── (llm.provider, llm.temperature)
├── travelops.postprocess
│   └── (validation_success)
└── travelops.state.save
```

### Using Traces in Tests

```python
def merit_test(travelops_agent, trace_context):
    response = travelops_agent.run("Find hotels")
    
    # Get tool spans
    all_spans = trace_context.get_all_spans()
    tool_spans = [s for s in all_spans if "tool.call" in s.name]
    
    # Assert tool was called
    assert len(tool_spans) > 0
    
    # Check tool arguments
    tool_name = tool_spans[0].attributes.get("tool.name")
    assert tool_name == "search_hotels"
```

## Contributing

### Adding a New Fault Profile

1. Add profile to `tests/faults/profiles.py`
2. Implement patcher in `tests/faults/patchers.py`
3. Create test module `tests/merit_travelops_<cluster>.py`
4. Generate 30 cases in `tests/fixtures/scenarios.py`
5. Update this README

### Testing Your Changes

```bash
# Run baseline (should pass)
MERIT_FAULT_PROFILE=none merit test

# Run with your fault (should fail ~30 tests)
MERIT_FAULT_PROFILE=your_fault merit test --tag your_tag
```

## License

Talk to Mark

## Credits

Mark is awesome!

## Unified Failure Signature Format

Each failure signature in `failure_signature_collection_*.json` contains **two sections**:

### Clustering Data
Used by the clustering algorithm to group similar failures:
- `error_type`: Generalized error message (values replaced with placeholders)
- `assertion_expressions`: Normalized failed assertion code  
- `execution_flow`: SUT component execution path
- `anomaly_flags`: Behavioral indicators (validation failures, empty responses, etc.)

### Fix Generation Data
Used by AI to propose code fixes:
- `error_message`: Original detailed error (not generalized)
- `assertion_errors`: Full assertion error details
- `input_data`: Test case input parameters
- `expected_output`: Expected behavior/values from test
- `actual_output`: What the SUT actually returned (from traces)
- `code_locations`: File paths, line numbers, and functions from execution

### Example Structure
```json
{
  "case_id": "abc-123",
  "test_name": "merit_grounding_enforcement",
  "test_module": "/path/to/test_file.py",
  
  "clustering": {
    "error_type": "Response contains unsupported facts. Response: [DETAILS]",
    "assertion_expressions": ["not has_hallucinations"],
    "execution_flow": ["agent.run", "llm.generate", "postprocess"],
    "anomaly_flags": {"has_validation_failure": false}
  },
  
  "fix_context": {
    "error_message": "Response contains unsupported facts (hallucination). Response: Paris has extensive transportation...",
    "input_data": {"prompt": "What transportation is available?"},
    "expected_output": {"facts_from_kb": true},
    "actual_output": {"llm_response": "Paris has extensive..."},
    "code_locations": [
      {"component": "llm.generate", "filepath": "/app/llm.py", "lineno": 45}
    ]
  }
}
```

### Why Two Sections?

**Clustering needs generalized data** to group similar failures:
- "Error: Missing field [VALUE]" groups all missing field errors
- Regardless of which specific field is missing

**Fix generation needs specific data** to propose fixes:
- "Error: Missing field 'destination'" tells AI exactly what to fix
- Along with code locations, inputs, and outputs for context

This unified format enables both efficient clustering (20 clusters) and accurate fix proposals (sent to AI with full context).
