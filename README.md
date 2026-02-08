# Better Coverage - Contract Discovery

A Claude Code Agent that analyzes Python codebases to discover all explicit and implicit contracts.


## Sample Output

```md
──────────────────────────────────────────────────────── Coverage Summary ─────────────────────────────────────────────────────────╮
│                                                                                                                                   │
│   Total obligations       35                                                                                                      │
│   Covered obligations     12 (34.3%)                                                                                              │
│   Uncovered obligations   23                                                                                                      │
│                                                                                                                                   │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                 Uncovered obligations (showing 10)                                                  
                                                                                                                                     
  ID               Severity   Enforcement   Location                   Description                                                   
 ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────── 
  OBL-SCHEMA-004   major      hard          app/schemas.py:18-19       Date fields must be in YYYY-MM-DD format                      
  OBL-GROUND-002   major      soft          app/prompting.py:96        Always cite knowledge base when referencing policies or       
                                                                       facts                                                         
  OBL-CONFIG-003   major      hard          app/agent.py:148-150       Agent must terminate when step count reaches max_agent_steps  
  OBL-PROMPT-001   major      hard          app/prompting.py:25-65     Messages must be assembled in order: system prompt, context   
                                                                       (if available),...                                            
  OBL-PROMPT-002   critical   hard          app/prompting.py:68-99     System prompt must define output format as JSON with          
                                                                       assistant_message and...                                      
  OBL-POST-002     minor      hard          app/postprocess.py:28-36   If dates are missing or None, default to                      
                                                                       start_date='2024-01-01' and...                                
  OBL-POST-003     minor      hard          app/postprocess.py:38-46   If destination is missing or None, default to city='Unknown'  
                                                                       and...                                                        
  OBL-POST-004     major      hard          app/postprocess.py:62-96   LLM response must be parsed to extract assistant_message and  
                                                                       itinerary from...                                             
  OBL-ROUTE-001    major      hard          app/router.py:14-16        Route must detect tool needs based on keywords: 'weather'     
                                                                       triggers...                                                   
  OBL-ROUTE-002    major      hard          app/router.py:18-30        Route must detect retrieval needs based on keywords: visa,    
                                                                       tipping, culture,...                                          
                                                                                                                                     
                          Tests considered (10)                          
                                                                         
  tests/merit_travelops_contract.py::merit_contract_json_schema          
  tests/merit_travelops_grounding.py::merit_grounding_enforcement        
  tests/merit_travelops_determinism.py::merit_determinism_config         
  tests/merit_travelops_prompting.py::merit_prompt_assembly_role_mixing  
  tests/merit_travelops_routing.py::merit_tool_routing_selection         
  tests/merit_travelops_postprocess.py::merit_postprocess_field_mapping  
  tests/merit_travelops_control_flow.py::merit_control_flow_termination  
  tests/merit_travelops_state.py::merit_state_memory_management          
  tests/merit_travelops_tool_args.py::merit_tool_argument_construction   
  tests/merit_travelops_retrieval.py::merit_retrieval_relevance          
                                                                         
                                                           Coverage Notes                                                            
  Coverage analysis identifies 23 uncovered obligations out of 54 total. Covered obligations include: basic schema structure         
  validation (OBL-SCHEMA-001/002/003), grounding enforcement via Merit predicates (OBL-GROUND-001/003), configuration temperature    
  and max steps checks (OBL-CONFIG-001/002/004), prompt coherence validation (OBL-PROMPT-003), postprocessing type validation        
  (OBL-POST-001), agent orchestration control flow (OBL-AGENT-001), and test contract validation (OBL-TEST-001). Uncovered           
  obligations require more granular unit/integration testing: date format regex validation, KB citation enforcement, max steps       
  termination logic, message ordering assertions, system prompt content verification, default value injection for missing fields,    
  LLM response JSON parsing, routing keyword detection, tool signature validation, budget filtering logic, session state defaults,   
  preference extraction from prompts, LLM client creation logic, JSON mode enforcement, stub LLM determinism, session_id UUID        
  generation, minimal itinerary fallback creation, and termination reason validation.                                                
                                                                                                                                     
╭───────────────────────────────────────────────────────────── Outputs ─────────────────────────────────────────────────────────────╮
│ Saved discovery results to /Users/nikitashirobokov/me/hackathon/results/contracts.json                                            │
│ Saved coverage results to /Users/nikitashirobokov/me/hackathon/results/coverage.json                                              │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

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

