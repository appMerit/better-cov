"""Fault profile definitions for clustered failure generation."""

import os
from dataclasses import dataclass


@dataclass
class FaultProfile:
    """Definition of a fault injection profile."""

    name: str
    description: str
    target_failures: int = 30


# Define all 10 fault profiles
FAULT_PROFILES = {
    "none": FaultProfile(
        name="none",
        description="No faults - baseline behavior",
        target_failures=0,
    ),
    "contract_json": FaultProfile(
        name="contract_json",
        description="Corrupt JSON or drop required fields at LLM output stage",
        target_failures=30,
    ),
    "prompt_role_mix": FaultProfile(
        name="prompt_role_mix",
        description="Omit system prompt or swap roles",
        target_failures=30,
    ),
    "retrieval_irrelevant": FaultProfile(
        name="retrieval_irrelevant",
        description="Return irrelevant docs or shuffle top-k",
        target_failures=30,
    ),
    "grounding_bypass": FaultProfile(
        name="grounding_bypass",
        description="Disable 'answer only from provided context' rule",
        target_failures=30,
    ),
    "router_wrong_tool": FaultProfile(
        name="router_wrong_tool",
        description="Router always returns 'final answer' (no tools)",
        target_failures=30,
    ),
    "tool_args_corrupt": FaultProfile(
        name="tool_args_corrupt",
        description="Corrupt tool args (dates, location, budget enum)",
        target_failures=30,
    ),
    "memory_disabled": FaultProfile(
        name="memory_disabled",
        description="Memory store returns empty or wrong session mapping",
        target_failures=30,
    ),
    "loop_termination_bug": FaultProfile(
        name="loop_termination_bug",
        description="Ignore step budget or stop too early",
        target_failures=30,
    ),
    "nondeterministic_config": FaultProfile(
        name="nondeterministic_config",
        description="Temperature set randomly per request",
        target_failures=30,
    ),
    "postprocess_mapping_bug": FaultProfile(
        name="postprocess_mapping_bug",
        description="Remap/drop fields during normalize/transform",
        target_failures=30,
    ),
}


def get_active_fault_profile() -> str:
    """Get the active fault profile from environment."""
    return os.getenv("MERIT_FAULT_PROFILE", "none")


def is_fault_active(profile_name: str) -> bool:
    """Check if a specific fault profile is active."""
    return get_active_fault_profile() == profile_name
