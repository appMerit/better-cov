# Better Coverage - Contract Discovery

A Claude Code Agent that analyzes Python codebases to discover all explicit and implicit contracts.

## What is a Contract?

A **contract** is any explicit or implicit requirement, constraint, or expectation about how a system should behave. Contracts can be:

### Hard Contracts (Explicit, Format-Based)
- **JSON Schemas / Pydantic Models**: Defined output structures
- **Type Hints**: Function signatures, return types
- **API Contracts**: REST endpoints, response formats
- **Data Formats**: Date formats (YYYY-MM-DD), string patterns, enums
- **Validation Rules**: Explicit validation logic in code

### Soft Contracts (Behavioral, Policy-Based)
- **Behavioral**: "Be friendly", "Be concise", "Use professional tone"
- **Policies**: "Never invent facts", "Always cite sources"
- **Constraints**: "Max 3 retries", "Must complete in <5s"
- **Guidelines**: "Prefer X over Y", "Should do Z when W"

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

The tool outputs a `ContractDiscoveryResult` JSON file containing:

```json
{
  "codebase_path": "path/to/analyzed/code",
  "total_contracts": 42,
  "contracts": [
    {
      "id": "contract_1",
      "type": "json_schema",
      "severity": "critical",
      "title": "TravelOpsResponse Schema",
      "description": "The response must follow this exact JSON structure...",
      "location": {
        "file_path": "app/schemas.py",
        "line_start": 63,
        "line_end": 69,
        "code_snippet": "class TravelOpsResponse(BaseModel):..."
      },
      "expected_behavior": "All API responses must conform to this schema",
      "violation_example": "Returning raw strings instead of structured JSON",
      "affected_components": ["agent.py", "postprocess.py"],
      "testable": true,
      "test_strategy": "Use pydantic validation to verify structure"
    }
  ],
  "summary": "Found 42 contracts: 15 hard contracts (JSON schemas, type hints)...",
  "contracts_by_type": {
    "json_schema": 8,
    "behavioral": 12,
    "policy": 6
  },
  "contracts_by_severity": {
    "critical": 10,
    "high": 15,
    "medium": 12,
    "low": 5
  }
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
