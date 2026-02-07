"""Expected schema definitions for validation."""

from typing import Any


def validate_itinerary_schema(itinerary: dict[str, Any], required_fields: list[str] | None = None) -> bool:
    """Validate that itinerary matches expected schema."""
    if required_fields is None:
        required_fields = ["destination", "dates", "flights", "hotels", "activities"]

    # Check all required fields are present
    for field in required_fields:
        if field not in itinerary:
            return False

    # Validate destination structure
    if "destination" in required_fields:
        dest = itinerary.get("destination", {})
        if not isinstance(dest, dict):
            return False
        if "city" not in dest or "country" not in dest:
            return False

    # Validate dates structure
    if "dates" in required_fields:
        dates = itinerary.get("dates", {})
        if not isinstance(dates, dict):
            return False
        if "start_date" not in dates or "end_date" not in dates:
            return False

    # Validate list fields
    for list_field in ["flights", "hotels", "activities"]:
        if list_field in required_fields:
            if not isinstance(itinerary.get(list_field, []), list):
                return False

    # Validate budget type if present
    if "budget" in itinerary and itinerary["budget"] is not None:
        if not isinstance(itinerary["budget"], (int, float)):
            return False

    return True


def validate_response_schema(response: dict[str, Any]) -> bool:
    """Validate that response has required top-level fields."""
    required_fields = ["assistant_message", "itinerary", "session_id"]
    return all(field in response for field in required_fields)


VALID_TERMINATION_REASONS = [
    "max_steps_reached",
    "complete",
    "success",
    "tool_complete",
    "final_answer",
]
