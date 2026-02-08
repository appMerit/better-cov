# Better Coverage - Contract Discovery

A Claude Code Agent that analyzes Python codebases to discover all explicit and implicit contracts.

## What is a Contract?

A **contract** is any explicit or implicit requirement, constraint, or expectation about how a system should behave. Contracts can be:

### Contract Obligations

Each `ContractObligation` groups related testable rules (`ObligationRule` objects):

**How to Express “Validator Type” in the Minimal Schema:**
The current schema is intentionally minimal and does not have a `validator` field.
Instead, encode the evaluation mechanism inside `ObligationRule.rule` using a clear prefix, for example:
- `jsonschema: TravelOpsResponse.model_validate(payload) succeeds`
- `deterministic_check: 0.0 <= temperature <= 1.0`
- `test_command: pytest tests/test_schemas.py::test_response_validation`
- `rubric: the response does not fabricate facts not present in context`

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

Run contract discovery and coverage rooted at a callable entrypoint (`{file.py}:{qualname}`):

```bash
# Using uv (recommended)
uv run better-cov merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__
```

### Advanced Options

```bash
# Increase max turns for thorough analysis
uv run better-cov merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__ --max-turns 150

# Quiet mode (no progress logging)
uv run better-cov merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__ --quiet

# Debug mode (detailed logging)
uv run better-cov merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__ --debug
```

### Command Line Arguments

- `callable_ref`: Callable reference string in the form `{file.py}:{qualname}` (required)
- `--max-turns`: Maximum turns for agent (default: 50)
- `--quiet`: Suppress progress logging
- `--debug`: Show detailed debug information

## Output Format

The tool writes outputs to `results/contracts.json` and `results/coverage.json` in the repo root.

`contracts.json` contains a `ContractDiscoveryResult` JSON file with executable `ContractObligation` objects:

```json
{
  "contracts": [
    {
      "name": "API Response Contract",
      "obligations": [
        {
          "id": "OBL-001",
          "location": "app/schemas.py:10-88",
          "description": "Response must match TravelOpsResponse schema",
          "rule": "jsonschema: TravelOpsResponse.model_validate(response) succeeds",
          "enforcement": "hard",
          "severity": "critical"
        }
      ]
    }
  ]
}
```

## Project Structure

```
better-cov/
├── app/
│   ├── models/
│   │   └── contract.py          # Contract data models
│   └── services/
│       ├── ast_analyzer/        # Callable-rooted AST mapper (wrapper import path)
│       ├── contract_discovery/
│       │   ├── agent.py         # Main agent implementation
│       │   ├── ast_analyzer/    # AST mapper implementation (parser/formatter)
│       │   └── prompts.py       # System prompts for agent
│       └── llm_driver/
│           ├── anthropic_handler.py  # Claude SDK wrapper
│           └── policies.py      # Agent policies and tools
├── merit-travelops-demo/        # Example codebase to analyze
├── app/cli.py                   # Main CLI entry point
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
uv run better-cov merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__
```

You'll see a Rich-formatted summary as the agent works:
```
🔍 Starting contract discovery for: merit-travelops-demo/tests/merit_travelops_contract.py:TravelOpsSUT.__call__
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
  - Date format `YYYY-MM-DD` (major)
  - Type hints in function signatures (minor)
  
- **Soft Contracts**:
  - "Be helpful travel planning AI" (minor)
  - "Never invent facts not in context" (critical)
  - "Always cite knowledge base" (major)
  - "Respect user preferences" (minor)

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
