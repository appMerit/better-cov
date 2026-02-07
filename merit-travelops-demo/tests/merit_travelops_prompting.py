"""Merit tests for prompt assembly and role mixing (Cluster 2)."""

import json

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_prompt_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_prompt_cases())
def merit_prompt_assembly_role_mixing(case: Case, travel_ops_sut):
    """Test that prompt assembly respects roles and format constraints."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Response must have valid structure with all required fields
    assert response.itinerary is not None, "Response must have itinerary"
    assert "destination" in response.itinerary, "Itinerary must have destination field"
    assert "dates" in response.itinerary, "Itinerary must have dates field"
    
    # Check that destination has required structure
    dest = response.itinerary.get("destination", {})
    assert isinstance(dest, dict), f"Destination must be dict, got {type(dest)}"
    assert "city" in dest, "Destination must have city"
    assert "country" in dest, "Destination must have country"
    
    # Check that response is coherent (not corrupted by role mixing)
    assert len(response.assistant_message) > 10, "Response message too short - likely corrupted"
    
    # Response should not contain obvious corruption artifacts
    msg_lower = response.assistant_message.lower()
    corruption_indicators = ["ignore", "random", "chatbot"]
    has_corruption = any(indicator in msg_lower for indicator in corruption_indicators)
    assert not has_corruption, f"Response contains corruption indicators: {msg_lower[:200]}"
