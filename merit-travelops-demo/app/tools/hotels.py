"""Hotel search tool."""

from typing import Any

from app.tracing import trace_operation


def search_hotels(
    location: str, check_in: str, check_out: str, budget: str | None = None
) -> dict[str, Any]:
    """Search for hotels in a location."""
    with trace_operation(
        "travelops.tool.call",
        {
            "tool.name": "search_hotels",
            "tool.args": f'{{"location": "{location}", "check_in": "{check_in}", "check_out": "{check_out}"}}',
        },
    ) as span:
        # Stub implementation
        hotels = [
            {
                "name": f"{location} Grand Hotel",
                "location": location,
                "price_per_night": 200.0,
                "rating": 4.5,
                "amenities": ["WiFi", "Pool", "Gym"],
            },
            {
                "name": f"{location} Budget Inn",
                "location": location,
                "price_per_night": 80.0,
                "rating": 3.5,
                "amenities": ["WiFi"],
            },
            {
                "name": f"{location} Luxury Resort",
                "location": location,
                "price_per_night": 450.0,
                "rating": 5.0,
                "amenities": ["WiFi", "Pool", "Gym", "Spa", "Restaurant"],
            },
        ]

        # Filter by budget if provided
        if budget:
            budget_lower = budget.lower()
            if "low" in budget_lower or "budget" in budget_lower:
                hotels = [h for h in hotels if h["price_per_night"] < 150]
            elif "high" in budget_lower or "luxury" in budget_lower:
                hotels = [h for h in hotels if h["price_per_night"] > 300]

        result = {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "hotels": hotels,
            "count": len(hotels),
        }

        span.set_attribute("tool.result_count", len(hotels))

        return result
