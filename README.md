# Better Coverage - Contract Discovery

A Claude Code Agent that analyzes Python codebases to discover all explicit and implicit contracts.

## What is a Contract?

A **contract** is any explicit or implicit requirement, constraint, or expectation about how a system should behave. Contracts can be:

### Contract Obligations

Each `ContractObligation` groups related testable rules (`ObligationRule` objects):

**Validator Types:**
- **jsonschema**: Pydantic models, JSON structures, data schemas
- **deterministic_check**: Boolean checks, format validation, field presence
- **test_command**: pytest tests, unit tests that can be executed
- **rubric**: LLM-judged quality (tone, helpfulness, accuracy)
- **manual**: Requirements that need human verification

**Enforcement Levels:**
- **hard**: Must pass or system fails (e.g., schema validation)
- **soft**: Contributes to quality score (e.g., tone preferences)

**Severity Levels:**
- **critical**: System breaks if violated
- **major**: Significant functionality impaired
- **minor**: Degraded experience or style issue

## Installation

1. Clone the repository:
```bash
git clone https://github.com/appMerit/better-cov.git
cd better-cov
```

2. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Usage

### Basic Usage

Run contract discovery on a codebase:

```bash
# Using uv (recommended)
uv run python run_discovery.py merit-travelops-demo/app

# Or directly with python
python run_discovery.py merit-travelops-demo/app
```

### Advanced Options

```bash
# Specify output file
uv run python run_discovery.py merit-travelops-demo/app -o results/contracts.json

# Increase max turns for thorough analysis
uv run python run_discovery.py merit-travelops-demo/app --max-turns 150

# Quiet mode (no progress logging)
uv run python run_discovery.py merit-travelops-demo/app --quiet

# Debug mode (detailed logging)
uv run python run_discovery.py merit-travelops-demo/app --debug
```

### Command Line Arguments

- `codebase_path`: Path to the codebase to analyze (required)
- `-o, --output`: Path to save results JSON file (default: `contracts_output.json`)
- `--max-turns`: Maximum turns for agent (default: 50)
- `--quiet`: Suppress progress logging
- `--debug`: Show detailed debug information

## Output Format

The tool outputs a `ContractDiscoveryResult` JSON file with executable `ContractObligation` objects:

```json
{
  "codebase_path": "path/to/analyzed/code",
  "total_contracts": 10,
  "contracts": [
    {
      "id": "contract.api-response.v1",
      "version": "1.0.0",
      "name": "API Response Contract",
      "target_agents": ["*"],
      "task_context": {
        "goal": "Return structured travel planning response",
        "inputs": {},
        "constraints": ["Must be valid JSON", "All required fields present"]
      },
      "output_contract": {
        "format": "json",
        "schema_definition": {},
        "required_fields": ["assistant_message", "itinerary", "session_id"]
      },
      "obligations": [
        {
          "id": "OBL-001",
          "description": "Response must match TravelOpsResponse schema",
          "applies_to": ["final_response"],
          "rule": "pydantic_validate(response, TravelOpsResponse) == success",
          "validator": "jsonschema",
          "enforcement": "hard",
          "severity": "critical",
          "weight": 1.0,
          "code_location": "schemas.py:63-69",
          "code_snippet": "class TravelOpsResponse(BaseModel): ..."
        },
        {
          "id": "OBL-002",
          "description": "All required fields must be present",
          "applies_to": ["final_response"],
          "rule": "check all required fields in dict",
          "validator": "deterministic_check",
          "enforcement": "hard",
          "severity": "critical",
          "weight": 1.0
        }
      ],
      "acceptance_policy": {
        "require_all_hard_obligations": true,
        "block_on": ["critical"],
        "use_weighted_scoring": true,
        "min_weighted_score": 0.9
      }
    }
  ],
  "summary": "Found 10 contracts with 28 obligations: 8 jsonschema, 12 deterministic_check, 6 rubric, 2 test_command validators"
}
```

## Project Structure

```
better-cov/
├── app/
│   ├── models/
│   │   └── contract.py          # Contract data models
│   └── services/
│       ├── contract_discovery/
│       │   ├── agent.py         # Main agent implementation
│       │   └── prompts.py       # System prompts for agent
│       └── llm_driver/
│           ├── anthropic_handler.py  # Claude SDK wrapper
│           └── policies.py      # Agent policies and tools
├── merit-travelops-demo/        # Example codebase to analyze
├── run_discovery.py             # Main CLI entry point
├── requirements.txt
└── README.md
```

## How It Works

1. **Initialize**: Creates a Claude Code Agent with read-only access to the codebase
2. **Explore**: Agent uses `glob`, `ls`, `grep` to explore the codebase structure
3. **Analyze**: Reads Python files systematically to find contracts
4. **Extract**: Identifies contracts in:
   - Pydantic models and schemas
   - Function type hints
   - System prompts for LLMs
   - Configuration values
   - Comments and docstrings
   - Validation logic
5. **Classify**: Categorizes each contract by type and severity
6. **Output**: Returns structured JSON with all findings

## Example: Analyzing merit-travelops-demo

```bash
uv run python run_discovery.py merit-travelops-demo/app
```

You'll see real-time progress as the agent works:
```
🔍 Starting contract discovery for: merit-travelops-demo/app
📊 Max turns: 50

🤖 Agent starting analysis...

🔄 Turn 1/50: Agent working...
🔄 Turn 2/50: Agent working...
...
✅ Agent completed in 25 turns
```

Expected findings:
- **Hard Contracts**: 
  - `TravelOpsResponse` schema (critical)
  - `Itinerary` structure (critical)
  - Date format `YYYY-MM-DD` (high)
  - Type hints in function signatures (medium)
  
- **Soft Contracts**:
  - "Be helpful travel planning AI" (medium)
  - "Never invent facts not in context" (critical)
  - "Always cite knowledge base" (high)
  - "Respect user preferences" (medium)

## Use Cases

1. **Test Generation**: Convert discovered contracts into automated tests
2. **Documentation**: Generate comprehensive contract documentation
3. **Code Review**: Identify missing or unclear contracts
4. **Onboarding**: Help new developers understand system requirements
5. **Compliance**: Verify system adheres to documented contracts

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
