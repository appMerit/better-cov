from __future__ import annotations

"""Minimal contract models for AI output obligations.

This is a narrow v1 focused on contract definition and validation.
Runtime orchestration and audit concerns are intentionally out of scope.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Severity(StrEnum):
    """Impact of a failed obligation."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ValidatorKind(StrEnum):
    """Mechanism used to evaluate an obligation."""

    JSON_SCHEMA = "jsonschema"
    DETERMINISTIC_CHECK = "deterministic_check"
    RUBRIC = "rubric"
    TEST_COMMAND = "test_command"
    MANUAL = "manual"


class EnforcementLevel(StrEnum):
    """Hard rules gate acceptance; soft rules are non-blocking expectations."""

    HARD = "hard"
    SOFT = "soft"


class OutputFormat(StrEnum):
    """Shape/channel expected from agent output."""

    JSON = "json"
    MARKDOWN = "markdown"
    CODE_PATCH = "code_patch"
    TEXT = "text"


class TaskContext(BaseModel):
    """Minimal task framing for the contract."""

    model_config = ConfigDict(extra="forbid")

    goal: str = Field(description="Primary objective the agent must satisfy.")
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured inputs for this task (parameters, facts, artifacts).",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard boundaries that the output must respect.",
    )

    @field_validator("goal")
    @classmethod
    def goal_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("goal must not be blank")
        return value

    @field_validator("constraints")
    @classmethod
    def constraints_must_be_non_empty_and_unique(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("constraints entries must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("constraints entries must be unique")
        return normalized


class OutputContract(BaseModel):
    """Expected output format and structural requirements."""

    model_config = ConfigDict(extra="forbid")

    format: OutputFormat = Field(description="Output representation expected from the agent.")
    schema_definition: dict[str, Any] = Field(
        default_factory=dict,
        description="Schema definition used by schema validators (typically JSON Schema).",
    )
    required_fields: list[str] = Field(
        default_factory=list,
        description="Required object fields when output format is structured.",
    )

    @field_validator("required_fields")
    @classmethod
    def required_fields_must_be_non_empty_and_unique(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("required_fields entries must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("required_fields entries must be unique")
        return normalized


class ObligationRule(BaseModel):
    """A single rule that can be evaluated by tests or validators."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique identifier for this obligation.")
    description: str = Field(description="Human-readable explanation of the requirement.")
    applies_to: list[str] = Field(
        min_length=1,
        description="Targets affected by this rule (for example `all`, `final_response`, `module:x`).",
    )
    rule: str = Field(description="Machine-checkable condition or rubric statement.")
    validator: ValidatorKind = Field(description="Validator type used to evaluate `rule`.")
    enforcement: EnforcementLevel = Field(
        default=EnforcementLevel.HARD,
        description="Hard rules gate acceptance; soft rules are non-blocking expectations.",
    )
    severity: Severity = Field(default=Severity.MAJOR, description="Impact when the rule fails.")

    @field_validator("id", "description", "rule")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("applies_to")
    @classmethod
    def applies_to_must_be_non_empty_and_unique(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("applies_to entries must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("applies_to entries must be unique")
        return normalized


class AcceptancePolicy(BaseModel):
    """Contract-level pass/fail logic."""

    model_config = ConfigDict(extra="forbid")

    require_all_hard_obligations: bool = Field(
        default=True,
        description="If true, all hard obligations must pass.",
    )
    block_on: set[Severity] = Field(
        default_factory=lambda: {Severity.CRITICAL},
        description="Failed obligations at these severities always block acceptance.",
    )


class ContractObligation(BaseModel):
    """Top-level contract used by tests and validators."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable contract identifier.")
    version: str = Field(description="Contract version string.")
    name: str | None = Field(default=None, description="Optional display name.")
    task_context: TaskContext = Field(description="Task framing context.")
    output_contract: OutputContract = Field(description="Output format/schema requirements.")
    obligations: list[ObligationRule] = Field(
        min_length=1,
        description="Rules that define expected behavior.",
    )
    acceptance_policy: AcceptancePolicy = Field(
        default_factory=AcceptancePolicy,
        description="How obligation results roll up into final pass/fail.",
    )

    @field_validator("id", "version")
    @classmethod
    def required_identifiers_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("name")
    @classmethod
    def optional_name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @model_validator(mode="after")
    def obligation_ids_must_be_unique(self) -> "ContractObligation":
        obligation_ids = [obligation.id for obligation in self.obligations]
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("obligation ids must be unique")
        return self

    @property
    def contract_key(self) -> str:
        """Stable key for snapshots and coverage maps."""
        return f"{self.id}:{self.version}"


__all__ = [
    "AcceptancePolicy",
    "ContractObligation",
    "EnforcementLevel",
    "ObligationRule",
    "OutputContract",
    "OutputFormat",
    "Severity",
    "TaskContext",
    "ValidatorKind",
]
