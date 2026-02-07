"""Merit tests for tool routing and selection (Cluster 5)."""

from merit import Case, iter_cases, resource, sut

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_routing_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_routing_cases())
def merit_tool_routing_selection(case: Case, travel_ops_sut):
    """Test that router selects correct tools for requests."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Get expected tool from case
    expected_tool = case.references.get("expected_tool")

    if expected_tool:
        # Check that response shows evidence of tool usage
        response_text = response.assistant_message.lower()
        
        # Different tools should produce different content patterns
        if expected_tool == "get_weather":
            # Weather responses should mention temperature, weather conditions, etc.
            weather_keywords = ["weather", "temperature", "°c", "humidity", "wind", "cloudy", "sunny"]
            has_weather_content = any(keyword in response_text for keyword in weather_keywords)
            assert has_weather_content, f"Expected weather information in response for {expected_tool}. Response: {response_text[:200]}"
        
        elif expected_tool == "search_hotels":
            # Hotel responses should mention hotels, accommodation, price per night, etc.
            hotel_keywords = ["hotel", "accommodation", "per night", "rating", "amenities"]
            has_hotel_content = any(keyword in response_text for keyword in hotel_keywords) or len(response.itinerary.get("hotels", [])) > 0
            assert has_hotel_content, f"Expected hotel information in response for {expected_tool}. Response: {response_text[:200]}"
        
        elif expected_tool == "search_flights":
            # Flight responses should mention flights, airline, duration, etc.
            flight_keywords = ["flight", "airline", "departure", "arrival", "duration", "stops"]
            has_flight_content = any(keyword in response_text for keyword in flight_keywords) or len(response.itinerary.get("flights", [])) > 0
            assert has_flight_content, f"Expected flight information in response for {expected_tool}. Response: {response_text[:200]}"

    # Response should be valid
    assert response.itinerary is not None, "Response must include itinerary"
    assert len(response.assistant_message) > 0, "Response must include assistant message"
