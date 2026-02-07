"""Example contracts for common usage patterns."""

from __future__ import annotations

from better_cov.contracts import (
    AcceptancePolicy,
    ContractObligation,
    EnforcementLevel,
    ObligationRule,
    OutputContract,
    OutputFormat,
    Severity,
    TaskContext,
    ValidatorKind,
)


def strict_ci_contract() -> ContractObligation:
    """Strict contract where all rules are hard gates."""

    return ContractObligation(
        id="contract.strict-ci.v1",
        name="Strict CI Contract",
        version="1.0.0",
        task_context=TaskContext(
            goal="Generate a production-ready patch and tests",
            inputs={"repo": "backend-service"},
            constraints=["No breaking API changes", "Keep public behavior stable"],
        ),
        output_contract=OutputContract(
            format=OutputFormat.CODE_PATCH,
            schema_definition={"type": "object", "required": ["summary", "diff", "tests"]},
            required_fields=["summary", "diff", "tests"],
        ),
        obligations=[
            ObligationRule(
                id="OBL-CI-001",
                description="Patch output must satisfy schema",
                applies_to=["final_output"],
                rule="jsonschema_valid == true",
                validator=ValidatorKind.JSON_SCHEMA,
                enforcement=EnforcementLevel.HARD,
                severity=Severity.CRITICAL,
            ),
            ObligationRule(
                id="OBL-CI-002",
                description="Tests must pass",
                applies_to=["repo/tests"],
                rule="pytest_exit_code == 0",
                validator=ValidatorKind.TEST_COMMAND,
                enforcement=EnforcementLevel.HARD,
                severity=Severity.CRITICAL,
            ),
        ],
        acceptance_policy=AcceptancePolicy(
            require_all_hard_obligations=True,
            block_on={Severity.CRITICAL, Severity.MAJOR},
        ),
    )


def friendly_assistant_contract() -> ContractObligation:
    """Mixed contract with hard safety and soft style expectations."""

    return ContractObligation(
        id="contract.friendly-assistant.v1",
        name="Friendly Assistant Contract",
        version="1.0.0",
        task_context=TaskContext(
            goal="Answer accurately with friendly tone",
            constraints=["No unsafe advice"],
        ),
        output_contract=OutputContract(
            format=OutputFormat.MARKDOWN,
            required_fields=["answer"],
        ),
        obligations=[
            ObligationRule(
                id="OBL-SAFE-001",
                description="No policy violations",
                applies_to=["all"],
                rule="policy_violations == 0",
                validator=ValidatorKind.DETERMINISTIC_CHECK,
                enforcement=EnforcementLevel.HARD,
                severity=Severity.CRITICAL,
            ),
            ObligationRule(
                id="OBL-TONE-001",
                description="Tone should be friendly",
                applies_to=["final_user_response"],
                rule="friendliness_score >= 0.7",
                validator=ValidatorKind.RUBRIC,
                enforcement=EnforcementLevel.SOFT,
                severity=Severity.MINOR,
            ),
        ],
        acceptance_policy=AcceptancePolicy(
            require_all_hard_obligations=True,
            block_on={Severity.CRITICAL},
        ),
    )


def all_example_contracts() -> list[ContractObligation]:
    """Convenience helper returning bundled examples."""

    return [strict_ci_contract(), friendly_assistant_contract()]


__all__ = ["all_example_contracts", "friendly_assistant_contract", "strict_ci_contract"]
