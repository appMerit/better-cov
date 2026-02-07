#!/bin/bash
# Run all Merit tests with or without faults
#
# USAGE:
#   ./scripts/run_all_faults.sh <mode> [traces]
#
# ARGUMENTS:
#   mode    - 'baseline' or 'faults' (required)
#   traces  - Add 'traces' to enable OpenTelemetry tracing (optional)
#
# EXAMPLES:
#   # Baseline mode - no faults, no traces (fast)
#   ./scripts/run_all_faults.sh baseline
#
#   # Baseline mode with traces
#   ./scripts/run_all_faults.sh baseline traces
#
#   # Fault mode - inject faults, no traces
#   ./scripts/run_all_faults.sh faults
#
#   # Fault mode with traces (full observability)
#   ./scripts/run_all_faults.sh faults traces

set -e

# Parse arguments
MODE="${1:-faults}"
ENABLE_TRACES="${2:-}"

if [[ "$MODE" != "baseline" && "$MODE" != "faults" ]]; then
    echo "Error: Invalid mode. Use 'baseline' or 'faults'"
    echo ""
    echo "Usage:"
    echo "  ./scripts/run_all_faults.sh <mode> [traces]"
    echo ""
    echo "Examples:"
    echo "  ./scripts/run_all_faults.sh baseline        # No faults, no traces"
    echo "  ./scripts/run_all_faults.sh baseline traces # No faults, with traces"
    echo "  ./scripts/run_all_faults.sh faults          # With faults, no traces"
    echo "  ./scripts/run_all_faults.sh faults traces   # With faults, with traces"
    exit 1
fi

# Define test files and their associated fault profiles
declare -a TESTS=(
    "tests/merit_travelops_contract.py:contract_json"
    "tests/merit_travelops_prompting.py:prompt_role_mix"
    "tests/merit_travelops_retrieval.py:retrieval_irrelevant"
    "tests/merit_travelops_grounding.py:grounding_bypass"
    "tests/merit_travelops_routing.py:router_wrong_tool"
    "tests/merit_travelops_tool_args.py:tool_args_corrupt"
    "tests/merit_travelops_state.py:memory_disabled"
    "tests/merit_travelops_control_flow.py:loop_termination_bug"
    "tests/merit_travelops_determinism.py:nondeterministic_config"
    "tests/merit_travelops_postprocess.py:postprocess_mapping_bug"
)

if [[ "$MODE" == "baseline" ]]; then
    echo "Running all tests in BASELINE mode (no faults)..."
    echo "Expected: Tests should pass or have minimal failures"
else
    echo "Running all tests with FAULTS injected..."
    echo "Expected: Tests should have failures"
fi

if [[ "$ENABLE_TRACES" == "traces" ]]; then
    echo "Tracing: ENABLED (traces will be saved to traces/ directory)"
    # Create traces directory if it doesn't exist
    mkdir -p traces
else
    echo "Tracing: DISABLED (use 'traces' argument to enable)"
fi
echo "===================================================="
echo ""

# Run each test
for test_spec in "${TESTS[@]}"; do
    IFS=':' read -r test_file fault_profile <<< "$test_spec"
    
    # Extract tag from filename for trace output
    tag=$(basename "$test_file" .py | sed 's/merit_travelops_//')
    
    # Build trace flags if enabled
    if [[ "$ENABLE_TRACES" == "traces" ]]; then
        if [[ "$MODE" == "baseline" ]]; then
            TRACE_FLAGS="--trace --trace-output traces/traces-${tag}-baseline.jsonl"
        else
            TRACE_FLAGS="--trace --trace-output traces/traces-${tag}-faults.jsonl"
        fi
    else
        TRACE_FLAGS=""
    fi
    
    if [[ "$MODE" == "baseline" ]]; then
        echo "Running: $test_file (no faults)"
        echo "----------------------------------------------"
        MERIT_FAULT_PROFILE="none" uv run merit test "$test_file" $TRACE_FLAGS \
            || echo "⚠ Some failures"
    else
        echo "Running: $test_file with fault=$fault_profile"
        echo "----------------------------------------------"
        MERIT_FAULT_PROFILE="$fault_profile" uv run merit test "$test_file" $TRACE_FLAGS \
            || echo "✗ Expected failures"
    fi
    
    echo ""
done

echo "===================================================="
if [[ "$MODE" == "baseline" ]]; then
    echo "Baseline testing completed!"
else
    echo "Fault-injected testing completed!"
fi
