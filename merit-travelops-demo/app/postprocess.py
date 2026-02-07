"""Postprocessing and normalization of LLM outputs."""

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas import Itinerary
from app.tracing import trace_operation


def normalize_itinerary(raw_itinerary: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate itinerary data."""
    with trace_operation("travelops.postprocess", {"raw_keys": len(raw_itinerary.keys())}) as span:
        try:
            # Validate against schema
            validated = Itinerary(**raw_itinerary)
            normalized = validated.model_dump()
            span.set_attribute("validation_success", True)
            return normalized
        except ValidationError as e:
            # Try to salvage what we can
            span.set_attribute("validation_success", False)
            span.set_attribute("validation_errors", str(e))

            # Get dates and ensure no None values
            dates = raw_itinerary.get("dates", {})
            if not dates or not isinstance(dates, dict):
                dates = {"start_date": "2024-01-01", "end_date": "2024-01-01"}
            else:
                # Fix None values in dates
                if dates.get("start_date") is None:
                    dates["start_date"] = "2024-01-01"
                if dates.get("end_date") is None:
                    dates["end_date"] = "2024-01-01"
            
            # Get destination and ensure no None values
            destination = raw_itinerary.get("destination", {})
            if not destination or not isinstance(destination, dict):
                destination = {"city": "Unknown", "country": "Unknown"}
            else:
                if not destination.get("city"):
                    destination["city"] = "Unknown"
                if not destination.get("country"):
                    destination["country"] = "Unknown"

            # Ensure required fields
            normalized = {
                "destination": destination,
                "dates": dates,
                "flights": raw_itinerary.get("flights", []),
                "hotels": raw_itinerary.get("hotels", []),
                "activities": raw_itinerary.get("activities", []),
                "budget": raw_itinerary.get("budget"),
                "notes": raw_itinerary.get("notes"),
            }

            return normalized


def parse_llm_response(response: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Parse LLM response to extract message and itinerary.
    
    Expects JSON mode output with structure:
    {
        "assistant_message": "...",
        "itinerary": {...}
    }
    """
    content = response.get("content", "")

    # Check if response has itinerary field directly (stub LLM format)
    if "itinerary" in response:
        return content, response["itinerary"]

    # Parse JSON content (OpenAI JSON mode)
    try:
        parsed = json.loads(content)
        assistant_message = parsed.get("assistant_message", "")
        itinerary = parsed.get("itinerary", {})
        return assistant_message, itinerary
    except json.JSONDecodeError as e:
        # Fallback: if JSON parsing fails, extract from markdown (backward compat)
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                assistant_message = parsed.get("assistant_message", content)
                itinerary = parsed.get("itinerary", {})
                return assistant_message, itinerary
            except json.JSONDecodeError:
                pass
        
        # Last resort: treat as plain text with empty itinerary
        return content, {}


def validate_response_schema(response: dict[str, Any]) -> bool:
    """Validate that response has required fields."""
    required_fields = {"assistant_message", "itinerary", "session_id"}
    return all(field in response for field in required_fields)
