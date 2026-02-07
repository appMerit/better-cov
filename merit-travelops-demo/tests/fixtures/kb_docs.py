"""Knowledge base document fixtures for testing."""

# Expected KB facts for grounding tests
EXPECTED_KB_FACTS = {
    "visa_france": "US citizens can visit France for up to 90 days without a visa for tourism",
    "visa_japan": "US citizens can visit Japan for up to 90 days without a visa for tourism",
    "tipping_france": "Service charge is included in restaurant bills. Additional tipping of 5-10% is appreciated",
    "tipping_japan": "Tipping is not customary and may be considered rude",
    "weather_paris": "Summer (June-August) averages 20-25°C",
    "weather_tokyo": "Humid summers (June-August) with temperatures 25-35°C",
    "budget_paris": "Expect $150-200/day for mid-range travel",
    "budget_tokyo": "Expect $120-180/day for mid-range travel",
}

# Policy texts for testing
POLICIES = {
    "grounding_policy": "Agent must only use information from the provided knowledge base. Never invent facts.",
    "tool_usage_policy": "Agent must call weather tool when asked about weather conditions.",
    "hotel_search_policy": "Agent must call hotel search tool when asked about accommodations.",
    "flight_search_policy": "Agent must call flight search tool when asked about flights.",
    "json_format_policy": "Agent must always respond with valid JSON containing assistant_message and itinerary fields.",
}
