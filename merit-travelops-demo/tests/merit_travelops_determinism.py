"""Merit tests for determinism and config drift (Cluster 9)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_determinism_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_determinism_cases())
def merit_determinism_config(case: Case, travel_ops_sut):
    """Test that configuration is deterministic and consistent."""
    # Check temperature if specified
    if case.sut_input_values.get("check_temperature", False):
        expected_temp = case.references.get("expected_temperature", 0.0)
        actual_temp = travel_ops_sut.agent.config.temperature

        assert (
            abs(actual_temp - expected_temp) < 0.01
        ), f"Temperature drift detected: expected {expected_temp}, got {actual_temp}"

    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(prompt=case.sut_input_values["prompt"])

    # For format-sensitive cases, check strict formatting
    if case.references.get("format_sensitive", False):
        # Response should have valid structure
        assert response.itinerary is not None, "Format-sensitive request must produce itinerary"

        # Check required fields
        assert "destination" in response.itinerary, "Missing destination field"
        assert "dates" in response.itinerary, "Missing dates field"

    # For consistency checks, run multiple times
    if case.sut_input_values.get("check_consistency", False):
        repeat_count = case.references.get("repeat_count", 2)
        results = [response]

        for _ in range(repeat_count - 1):
            repeat_response = travel_ops_sut(prompt=case.sut_input_values["prompt"])
            results.append(repeat_response)

        # Check that key fields are consistent
        destinations = [r.itinerary.get("destination", {}).get("city") for r in results]

        # All destinations should be the same (or None)
        non_none_dests = [d for d in destinations if d]
        if len(non_none_dests) > 1:
            assert all(
                d == non_none_dests[0] for d in non_none_dests
            ), f"Inconsistent destinations across runs: {destinations}"

        # Message lengths should be similar (within 50% variation)
        msg_lengths = [len(r.assistant_message) for r in results]
        if msg_lengths:
            avg_length = sum(msg_lengths) / len(msg_lengths)
            for length in msg_lengths:
                variation = abs(length - avg_length) / avg_length if avg_length > 0 else 0
                assert (
                    variation < 0.5
                ), f"High variation in message lengths: {msg_lengths} (avg: {avg_length})"

    # JSON format requirement
    if case.references.get("must_be_json", False):
        # Should have structured itinerary
        assert isinstance(
            response.itinerary, dict
        ), f"Expected dict itinerary, got {type(response.itinerary)}"
