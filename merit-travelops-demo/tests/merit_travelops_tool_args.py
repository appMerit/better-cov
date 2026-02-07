"""Merit tests for tool argument construction (Cluster 6)."""

import json

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_tool_args_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_tool_args_cases())
def merit_tool_argument_construction(case: Case, travel_ops_sut):
    """Test that tool arguments are constructed correctly."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Get expected location from case
    expected_location = case.references.get("location")

    # Response should be valid and contain expected information
    assert response.itinerary is not None, "Response must include itinerary"
    assert len(response.assistant_message) > 0, "Response must include assistant message"
    
    # Response should be substantive (not just generic acknowledgment)
    # Tool arg corruption makes responses generic, so this catches it
    assert len(response.assistant_message) > 50, (
        f"Response too short/generic. Tool arguments may be corrupted. "
        f"Response: {response.assistant_message}"
    )
    
    # Response should not be a generic non-answer
    generic_phrases = ["i can help with that", "let me provide", "i can assist"]
    response_lower = response.assistant_message.lower()
    is_generic = any(phrase in response_lower for phrase in generic_phrases)
    
    assert not is_generic or len(response.assistant_message) > 100, (
        f"Response appears to be generic/corrupted (likely bad tool args). "
        f"Response: {response.assistant_message[:200]}"
    )
    
    # Check that response mentions the expected location if specified
    if expected_location:
        response_text = (response.assistant_message + " " + 
                        str(response.itinerary)).lower()
        assert expected_location.lower() in response_text, (
            f"Response should mention expected location '{expected_location}'. "
            f"Response: {response.assistant_message[:200]}"
        )
