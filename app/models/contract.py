"""Minimal contract models for AI output obligations.

This is a narrow v1 focused on contract definition and validation.
Runtime orchestration and audit concerns are intentionally out of scope.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Severity(StrEnum):
    """Impact of a failed obligation."""

    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"

class EnforcementLevel(StrEnum):
    """Hard rules gate acceptance; soft rules are non-blocking expectations."""

    HARD = "hard"
    SOFT = "soft"


class ObligationRule(BaseModel):
    """A single rule that can be evaluated by tests or validators."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Unique identifier for this obligation.")
    location: str = Field(description="Location of the obligation in the codebase.")
    description: str = Field(description="Human-readable explanation of the requirement.")
    rule: str = Field(description="Machine-checkable condition or rubric statement.")
    enforcement: EnforcementLevel = Field(
        default=EnforcementLevel.HARD,
        description="Hard rules gate acceptance; soft rules are non-blocking expectations.",
    )
    severity: Severity = Field(default=Severity.MAJOR, description="Impact when the rule fails.")


class ContractObligation(BaseModel):
    """Top-level contract used by tests and validators."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Display name.")
    obligations: list[ObligationRule] = Field(
        min_length=1,
        description="Rules that define expected behavior.",
    )

class ContractDiscoveryResult(BaseModel):
    """Result of contract discovery."""

    model_config = ConfigDict(extra="forbid")

    contracts: list[ContractObligation] = Field(description="List of discovered contracts.")


class ContractCoverageResult(BaseModel):
    """Result of contract coverage analysis."""

    model_config = ConfigDict(extra="forbid")

    codebase_path: str = Field(description="Root path of the analyzed codebase.")
    callable_ref: str = Field(description="Callable reference for the SUT entrypoint.")
    uncovered_obligation_ids: list[str] = Field(
        default_factory=list,
        description="Obligation IDs not covered by the discovered tests.",
    )
    discovered_test_refs: list[str] = Field(
        default_factory=list,
        description="Test references examined for coverage (e.g., path.py::test_name).",
    )
    notes: str | None = Field(
        default=None,
        description="Optional rationale or caveats about coverage decisions.",
    )

__all__ = [
    "ContractObligation",
    "EnforcementLevel",
    "ContractDiscoveryResult",
    "ContractCoverageResult",
    "ObligationRule",
    "Severity",
]
