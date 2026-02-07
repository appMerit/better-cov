"""Merit tests for postprocessing and field mapping (Cluster 10)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.expected_schemas import validate_itinerary_schema
from tests.fixtures.scenarios import generate_postprocess_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_postprocess_cases())
def merit_postprocess_field_mapping(case: Case, travel_ops_sut):
    """Test that postprocessing correctly maps and validates fields."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(prompt=case.sut_input_values["prompt"])

    # Get required schema fields from case
    required_fields = case.references.get(
        "required_schema_fields", ["destination", "dates"]
    )

    # Validate schema
    assert validate_itinerary_schema(
        response.itinerary, required_fields
    ), f"Schema validation failed. Required: {required_fields}, Got keys: {list(response.itinerary.keys())}"

    # Check specific field types
    if "destination" in response.itinerary:
        dest = response.itinerary["destination"]
        assert isinstance(dest, dict), f"destination must be dict, got {type(dest)}"
        assert "city" in dest, "destination must have 'city' field"
        assert "country" in dest, "destination must have 'country' field"
        assert isinstance(dest["city"], str), f"city must be string, got {type(dest['city'])}"
        assert isinstance(
            dest["country"], str
        ), f"country must be string, got {type(dest['country'])}"

    if "dates" in response.itinerary:
        dates = response.itinerary["dates"]
        assert dates is not None, "dates must not be None"
        assert isinstance(dates, dict), f"dates must be dict, got {type(dates)}"
        assert "start_date" in dates, "dates must have 'start_date' field"
        assert "end_date" in dates, "dates must have 'end_date' field"
        # Dates should be strings
        assert isinstance(
            dates["start_date"], str
        ), f"start_date must be string, got {type(dates['start_date'])}"
        assert isinstance(
            dates["end_date"], str
        ), f"end_date must be string, got {type(dates['end_date'])}"

    # Check list fields have correct types
    if "flights" in response.itinerary:
        flights = response.itinerary["flights"]
        assert isinstance(flights, list), f"flights must be list, got {type(flights)}"
        # Each flight should be a dict
        for flight in flights:
            assert isinstance(flight, dict), f"Each flight must be dict, got {type(flight)}"

    if "hotels" in response.itinerary:
        hotels = response.itinerary["hotels"]
        assert isinstance(hotels, list), f"hotels must be list, got {type(hotels)}"
        # Each hotel should be a dict
        for hotel in hotels:
            assert isinstance(hotel, dict), f"Each hotel must be dict, got {type(hotel)}"

    if "activities" in response.itinerary:
        activities = response.itinerary["activities"]
        assert isinstance(
            activities, list
        ), f"activities must be list, got {type(activities)}"
        # Each activity should be a dict
        for activity in activities:
            assert isinstance(
                activity, dict
            ), f"Each activity must be dict, got {type(activity)}"

    # Check budget type if present
    if "budget" in response.itinerary:
        budget = response.itinerary["budget"]
        if budget is not None:
            assert isinstance(
                budget, (int, float)
            ), f"budget must be number, got {type(budget)}"
            assert budget >= 0, f"budget must be non-negative, got {budget}"

    # Check notes type if present
    if "notes" in response.itinerary:
        notes = response.itinerary["notes"]
        if notes is not None:
            assert isinstance(notes, str), f"notes must be string, got {type(notes)}"

    # For full variation, check all fields are present
    if case.metadata.get("variation") == "full":
        assert (
            "budget" in response.itinerary or "notes" in response.itinerary
        ), "Full variation should include budget or notes"
