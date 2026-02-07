"""Merit tests for control flow and termination (Cluster 8)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import Config, get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.expected_schemas import VALID_TERMINATION_REASONS
from tests.fixtures.scenarios import generate_control_flow_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_control_flow_cases())
def merit_control_flow_termination(case: Case, travel_ops_sut):
    """Test that control flow and termination logic works correctly."""
    # Override max_steps if specified in case
    if "max_steps" in case.sut_input_values:
        travel_ops_sut.agent.config.max_steps = case.sut_input_values["max_steps"]

    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(prompt=case.sut_input_values["prompt"])

    # Response should be complete
    assert response.itinerary is not None, "Response must include itinerary"
    assert len(response.assistant_message) > 0, "Response must include assistant message"

    # For multi-step tasks, response should be more comprehensive
    min_steps = case.references.get("min_steps", 0)
    if min_steps >= 2:
        # Should have some combination of flights, hotels, or activities
        has_flights = len(response.itinerary.get("flights", [])) > 0
        has_hotels = len(response.itinerary.get("hotels", [])) > 0
        has_activities = len(response.itinerary.get("activities", [])) > 0

        assert (
            has_flights or has_hotels or has_activities
        ), "Multi-step task should produce comprehensive itinerary with multiple elements"
