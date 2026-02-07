#!/bin/bash
# Run all Merit tests with all faults and extract failure signatures from database
# Outputs a single JSON file with all failure signatures
#
# Usage: ./scripts/collect_all_failures.sh

set -e  # Exit on error

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="trace_reports/failure_signature_collection_${TIMESTAMP}.json"
TEMP_SIGNATURES_DIR="temp_signatures_${TIMESTAMP}"
DB_PATH=".merit/merit.db"

# Cleanup function
cleanup() {
    echo
    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_SIGNATURES_DIR" 2>/dev/null || true
}

# Trap to ensure cleanup on exit or interruption
trap cleanup EXIT INT TERM

echo "═══════════════════════════════════════════════════════════════"
echo "  Collecting All Failure Signatures"
echo "═══════════════════════════════════════════════════════════════"
echo "Timestamp: $TIMESTAMP"
echo "Output: $OUTPUT_FILE"
echo

# Clean up any leftover temp directories from previous runs
echo "Cleaning up old temp directories..."
rm -rf temp_signatures_* 2>/dev/null || true

# Clear LLM timing log for fresh data
echo "Clearing LLM timing log..."
rm -f .merit/llm_timing.log 2>/dev/null || true
echo "✓ Ready to collect timing data"
echo

# Create directories
echo "Creating directories..."
mkdir -p "$TEMP_SIGNATURES_DIR" || { echo "Failed to create $TEMP_SIGNATURES_DIR"; exit 1; }
mkdir -p trace_reports || { echo "Failed to create trace_reports"; exit 1; }
echo "✓ Directories created"
echo

# Define all test-fault pairs (parallel arrays)
TEST_FILES=(
    "tests/merit_travelops_contract.py"
    "tests/merit_travelops_prompting.py"
    "tests/merit_travelops_retrieval.py"
    "tests/merit_travelops_grounding.py"
    "tests/merit_travelops_routing.py"
    "tests/merit_travelops_tool_args.py"
    "tests/merit_travelops_state.py"
    "tests/merit_travelops_control_flow.py"
    "tests/merit_travelops_determinism.py"
    "tests/merit_travelops_postprocess.py"
)

FAULT_PROFILES=(
    "contract_json"
    "prompt_role_mix"
    "retrieval_irrelevant"
    "grounding_bypass"
    "router_wrong_tool"
    "tool_args_corrupt"
    "memory_disabled"
    "loop_termination_bug"
    "nondeterministic_config"
    "postprocess_mapping_bug"
)

TAGS=(
    "contract"
    "prompting"
    "retrieval"
    "grounding"
    "routing"
    "tool_args"
    "memory"
    "control_flow"
    "determinism"
    "postprocess"
)

TOTAL_TESTS=${#TEST_FILES[@]}

echo "═══════════════════════════════════════════════════════════════"
echo "  Running Tests with Fault Profiles"
echo "═══════════════════════════════════════════════════════════════"
echo

# Array to collect run_ids from each test execution
RUN_IDS=()

# Run each test with its fault profile
for i in $(seq 0 $((TOTAL_TESTS - 1))); do
    test_file="${TEST_FILES[$i]}"
    fault_profile="${FAULT_PROFILES[$i]}"
    tag="${TAGS[$i]}"
    
    echo "───────────────────────────────────────────────────────────────"
    echo "[$((i + 1))/$TOTAL_TESTS] Running: $test_file"
    echo "  Fault profile: $fault_profile"
    echo "  Tag: $tag"
    echo "───────────────────────────────────────────────────────────────"
    
    # Start timing
    TEST_START=$(date +%s)
    
    # Run test and capture output to extract run_id
    # Use --trace flag (saves to DB automatically)
    TEST_OUTPUT=$(MERIT_FAULT_PROFILE="$fault_profile" uv run merit test "$test_file" \
        --trace \
        2>&1) || true
    
    # End timing
    TEST_END=$(date +%s)
    TEST_DURATION=$((TEST_END - TEST_START))
    
    # Clean up JSONL trace file if created (we only use DB traces)
    rm -f .merit/traces.jsonl 2>/dev/null || true
    
    # Display the output
    echo "$TEST_OUTPUT"
    
    # Extract run_id from output
    RUN_ID=$(echo "$TEST_OUTPUT" | grep -o 'run_id: [a-f0-9-]*' | head -1 | cut -d' ' -f2)
    if [ -n "$RUN_ID" ]; then
        RUN_IDS+=("$RUN_ID")
        echo "Captured run_id: $RUN_ID"
        echo "⏱️  Total test time: ${TEST_DURATION}s (wall clock)"
    fi
    
    echo
done

echo "═══════════════════════════════════════════════════════════════"
echo "  Collected ${#RUN_IDS[@]} run_ids from test executions"
echo "═══════════════════════════════════════════════════════════════"
echo

echo "═══════════════════════════════════════════════════════════════"
echo "  Extracting Failure Signatures from Database"
echo "═══════════════════════════════════════════════════════════════"
echo

# Build SQL IN clause for run_ids
RUN_IDS_SQL=$(printf "'%s'," "${RUN_IDS[@]}" | sed 's/,$//')

if [ -z "$RUN_IDS_SQL" ]; then
    echo "❌ No run_ids collected from test runs!"
    exit 1
fi

# Get failed test case_ids from ONLY the current test runs
CASE_IDS=$(sqlite3 "$DB_PATH" "SELECT case_id FROM test_executions WHERE status = 'failed' AND run_id IN ($RUN_IDS_SQL) ORDER BY case_id;")

if [ -z "$CASE_IDS" ]; then
    echo "❌ No failed tests found in database for run_ids: ${RUN_IDS[@]}"
    exit 1
fi

FAIL_COUNT=$(echo "$CASE_IDS" | wc -l | tr -d ' ')
echo "Found $FAIL_COUNT failed test cases in database"
echo

# Extract signature for each failed case
PROCESSED=0
for case_id in $CASE_IDS; do
    PROCESSED=$((PROCESSED + 1))
    OUTPUT_SIGNATURE="$TEMP_SIGNATURES_DIR/${case_id}.json"
    
    # Extract signature from database (no trace file needed!)
    if python3 scripts/extract_failure_signature.py "$case_id" "$DB_PATH" > "$OUTPUT_SIGNATURE" 2>/dev/null; then
        # Verify the output is valid JSON
        if [ -s "$OUTPUT_SIGNATURE" ] && python3 -c "import json; json.load(open('$OUTPUT_SIGNATURE'))" 2>/dev/null; then
            printf "."
        else
            printf "x"
            rm -f "$OUTPUT_SIGNATURE"  # Delete invalid file
        fi
    else
        printf "x"
        rm -f "$OUTPUT_SIGNATURE"  # Delete empty file on failure
    fi
    
    # Print progress every 10 signatures
    if [ $((PROCESSED % 10)) -eq 0 ]; then
        printf " [$PROCESSED/$FAIL_COUNT]\n  "
    fi
done

# Final newline
if [ $((PROCESSED % 10)) -ne 0 ]; then
    echo
fi

echo
echo "✓ Extracted $FAIL_COUNT signatures"
echo

echo "═══════════════════════════════════════════════════════════════"
echo "  Creating Collection File"
echo "═══════════════════════════════════════════════════════════════"
echo

# Count total signatures
TOTAL_SIGNATURES=$(ls -1 "$TEMP_SIGNATURES_DIR"/*.json 2>/dev/null | wc -l | tr -d ' ')

if [ "$TOTAL_SIGNATURES" -eq 0 ]; then
    echo "❌ No failure signatures extracted!"
    exit 1
fi

echo "Total failure signatures: $TOTAL_SIGNATURES"
echo "Creating collection file..."

# Create the collection JSON - just an array of all signatures
python3 -c "
import json
import glob
import os

# Load all signatures
signatures = []
skipped = 0
for sig_file in sorted(glob.glob('$TEMP_SIGNATURES_DIR/*.json')):
    try:
        with open(sig_file, 'r') as f:
            content = f.read().strip()
            if not content:
                print(f'⚠️  Skipping empty file: {os.path.basename(sig_file)}')
                skipped += 1
                continue
            sig = json.loads(content)
            signatures.append(sig)
    except json.JSONDecodeError as e:
        print(f'⚠️  Skipping invalid JSON in {os.path.basename(sig_file)}: {e}')
        skipped += 1
    except Exception as e:
        print(f'⚠️  Error reading {os.path.basename(sig_file)}: {e}')
        skipped += 1

# Write to output file - just the array of signatures
with open('$OUTPUT_FILE', 'w') as f:
    json.dump(signatures, f, indent=2)

print(f'✓ Created {\"$OUTPUT_FILE\"}')
print(f'  Total failure signatures: {len(signatures)}')
if skipped > 0:
    print(f'  Skipped {skipped} invalid files')
"

echo
echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ Complete!"
echo "═══════════════════════════════════════════════════════════════"
echo "Output file: $OUTPUT_FILE"
echo
echo "View signatures:"
echo "  cat $OUTPUT_FILE | jq length"
echo "  cat $OUTPUT_FILE | jq '.[0]'  # First signature"
echo

# Analyze LLM timing if log exists
if [ -f ".merit/llm_timing.log" ]; then
    echo
    echo "═══════════════════════════════════════════════════════════════"
    echo "  📊 Analyzing LLM Call Timing"
    echo "═══════════════════════════════════════════════════════════════"
    echo
    python3 scripts/analyze_llm_timing.py
else
    echo
    echo "⚠️  No LLM timing data collected (log file not found)"
fi
echo
