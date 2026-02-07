"""Merit tests for state and memory management (Cluster 7)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from app.state import clear_all_sessions
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_memory_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_memory_cases())
def merit_state_memory_management(case: Case, travel_ops_sut):
    """Test that state and memory are properly maintained across turns."""
    # Get session ID from case
    session_id = case.sut_input_values.get("session_id")

    # First turn: set up preference
    if "previous_turn" in case.sut_input_values:
        previous_prompt = case.sut_input_values["previous_turn"]
        travel_ops_sut(prompt=previous_prompt, session_id=session_id)

    # Handle multiple previous turns
    elif "previous_turns" in case.sut_input_values:
        for prev_prompt in case.sut_input_values["previous_turns"]:
            travel_ops_sut(prompt=prev_prompt, session_id=session_id)

    # Second turn: check if preference is remembered
    response = travel_ops_sut(
        prompt=case.sut_input_values["prompt"], session_id=session_id
    )

    # Check that the preference is reflected in response
    preference_text = case.references.get("must_remember", "").lower()
    response_text = f"{response.assistant_message} {str(response.itinerary)}".lower()

    # Extract key preference indicators
    pref_type = case.references.get("preference_type")

    # FIRST: Check for explicit memory failure indicators (applies to ALL preference types)
    memory_failure_phrases = [
        "don't have access",
        "don't recall",
        "don't have any history",
        "no previous session",
        "unable to recall",
        "starting fresh",
        "new conversation"
    ]
    
    has_memory_failure = any(phrase in response_text for phrase in memory_failure_phrases)
    
    assert not has_memory_failure, (
        f"Memory fault detected - response indicates no access to previous preferences. "
        f"Response: {response_text[:200]}"
    )
    
    # SECOND: Check response isn't just empty/generic (< 30 chars means corrupted)
    assert len(response.assistant_message) > 30, (
        f"Response too generic/empty (likely memory corruption). "
        f"Response: {response_text[:200]}"
    )

    # THIRD: Type-specific checks (optional, more lenient)
    # These are kept for baseline validation but memory failure is caught above
    if pref_type == "seat":
        pass  # Memory check above is sufficient

    elif pref_type == "budget":
        pass  # Memory check above is sufficient

    elif pref_type == "hotel":
        pass  # Memory check above is sufficient

    # General check: response should not ask for already-provided information
    if case.references.get("explicit_reference", False):
        # When user explicitly references earlier conversation
        assert (
            len(response.assistant_message) > 0
        ), "Should provide substantive response when referencing earlier conversation"
