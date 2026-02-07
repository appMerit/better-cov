"""Contract models for representing discovered contracts in a codebase."""

from enum import Enum

from pydantic import BaseModel, Field


class ContractType(str, Enum):
    """Type of contract discovered."""

    # Hard contracts - explicit, testable format requirements
    JSON_SCHEMA = "json_schema"  # Pydantic models, JSON schemas
    TYPE_HINT = "type_hint"  # Python type hints, function signatures
    API_CONTRACT = "api_contract"  # API response formats, endpoints
    DATA_FORMAT = "data_format"  # Date formats, string patterns, enums
    VALIDATION_RULE = "validation_rule"  # Explicit validation logic
    
    # Soft contracts - behavioral requirements
    BEHAVIORAL = "behavioral"  # "Be friendly", "Be concise"
    POLICY = "policy"  # "Never invent facts", "Always cite sources"
    CONSTRAINT = "constraint"  # "Max 3 retries", "Must complete in 5s"
    GUIDELINE = "guideline"  # "Prefer X over Y", "Should do Z"


class ContractSeverity(str, Enum):
    """Severity/importance of the contract."""

    CRITICAL = "critical"  # System breaks if violated (e.g., JSON schema)
    HIGH = "high"  # Major functionality impaired
    MEDIUM = "medium"  # Degraded experience
    LOW = "low"  # Nice-to-have, stylistic


class CodeLocation(BaseModel):
    """Location of code in the repository."""

    file_path: str = Field(description="Relative path to file from repo root")
    line_start: int = Field(description="Starting line number")
    line_end: int = Field(description="Ending line number")
    code_snippet: str = Field(description="Actual code snippet (max 500 chars)", max_length=500)


class Contract(BaseModel):
    """A discovered contract in the codebase."""

    id: str = Field(description="Unique identifier (e.g. contract_1, contract_2)")
    type: ContractType = Field(description="Type of contract")
    severity: ContractSeverity = Field(description="Importance level")
    
    # Core information
    title: str = Field(description="Short descriptive title (max 100 chars)", max_length=100)
    description: str = Field(description="Detailed description (max 500 chars)", max_length=500)
    
    # Location
    location: CodeLocation = Field(description="Where the contract is defined")
    
    # Contract details
    expected_behavior: str = Field(
        description="What the system should do (max 300 chars)", max_length=300
    )
    
    # Testing information
    test_strategy: str = Field(
        description="How to test this contract (max 300 chars)", max_length=300
    )


class ContractDiscoveryResult(BaseModel):
    """Complete result of contract discovery analysis."""

    codebase_path: str = Field(description="Path to analyzed codebase")
    total_contracts: int = Field(description="Total number of contracts found")
    
    contracts: list[Contract] = Field(
        description="List of discovered contracts (10-20 contracts)"
    )
    
    summary: str = Field(
        description="High-level summary of discovered contracts (max 500 chars)", max_length=500
    )
