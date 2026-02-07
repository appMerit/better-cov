"""Merit tests for contract/JSON schema validation (Cluster 1)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.expected_schemas import validate_itinerary_schema, validate_response_schema
from tests.fixtures.scenarios import generate_contract_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_contract_cases())
def merit_contract_json_schema(case: Case, travel_ops_sut):
    """Test that responses conform to JSON schema contract."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Convert to dict for validation
    response_dict = response.model_dump()

    # Assert response has required top-level fields
    assert validate_response_schema(
        response_dict
    ), f"Response missing required fields: {response_dict.keys()}"

    # Assert assistant_message is a string
    assert isinstance(
        response.assistant_message, str
    ), f"assistant_message must be string, got {type(response.assistant_message)}"

    # Assert itinerary is present
    assert response.itinerary is not None, "itinerary field is missing"

    # Validate itinerary schema
    required_fields = case.references.get("required_fields", ["destination", "dates"])
    assert validate_itinerary_schema(
        response.itinerary, required_fields
    ), f"Itinerary schema validation failed. Missing fields from {required_fields}. Got: {response.itinerary.keys()}"

    # Check expected city if specified
    if "expected_city" in case.references:
        destination = response.itinerary.get("destination", {})
        assert (
            case.references["expected_city"].lower() in destination.get("city", "").lower()
        ), f"Expected city {case.references['expected_city']}, got {destination.get('city')}"
