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
    code_snippet: str = Field(description="Actual code snippet")


class Contract(BaseModel):
    """A discovered contract in the codebase."""

    id: str = Field(description="Unique identifier for this contract")
    type: ContractType = Field(description="Type of contract")
    severity: ContractSeverity = Field(description="Importance level")
    
    # Core information
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed description of the contract")
    
    # Location
    location: CodeLocation = Field(description="Where the contract is defined")
    
    # Contract details
    expected_behavior: str = Field(
        description="What the system should do to satisfy this contract"
    )
    violation_example: str | None = Field(
        default=None,
        description="Example of what would violate this contract"
    )
    
    # Context
    affected_components: list[str] = Field(
        default_factory=list,
        description="Which components/modules must adhere to this"
    )
    related_contracts: list[str] = Field(
        default_factory=list,
        description="IDs of related contracts"
    )
    
    # Testing information
    testable: bool = Field(
        default=True,
        description="Whether this can be automatically tested"
    )
    test_strategy: str | None = Field(
        default=None,
        description="How to test this contract"
    )


class ContractDiscoveryResult(BaseModel):
    """Complete result of contract discovery analysis."""

    codebase_path: str = Field(description="Path to analyzed codebase")
    total_contracts: int = Field(description="Total number of contracts found")
    
    contracts: list[Contract] = Field(
        default_factory=list,
        description="All discovered contracts"
    )
    
    summary: str = Field(
        description="High-level summary of discovered contracts"
    )
    
    # Statistics
    contracts_by_type: dict[ContractType, int] = Field(
        default_factory=dict,
        description="Count of contracts by type"
    )
    contracts_by_severity: dict[ContractSeverity, int] = Field(
        default_factory=dict,
        description="Count of contracts by severity"
    )
