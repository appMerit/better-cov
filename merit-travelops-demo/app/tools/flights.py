"""Flight search tool."""

from typing import Any

from app.tracing import trace_operation


def search_flights(
    from_location: str, to_location: str, date: str, budget: str | None = None
) -> dict[str, Any]:
    """Search for flights between locations."""
    # Handle both 'from' and 'from_location' parameter names
    from_loc = from_location

    with trace_operation(
        "travelops.tool.call",
        {
            "tool.name": "search_flights",
            "tool.args": f'{{"from": "{from_loc}", "to": "{to_location}", "date": "{date}"}}',
        },
    ) as span:
        # Stub implementation
        flights = [
            {
                "departure": from_loc,
                "arrival": to_location,
                "date": date,
                "airline": "Air France",
                "price": 850.0,
                "duration": "8h 30m",
                "stops": 0,
            },
            {
                "departure": from_loc,
                "arrival": to_location,
                "date": date,
                "airline": "Budget Air",
                "price": 520.0,
                "duration": "12h 15m",
                "stops": 1,
            },
            {
                "departure": from_loc,
                "arrival": to_location,
                "date": date,
                "airline": "Premium Airways",
                "price": 1500.0,
                "duration": "7h 45m",
                "stops": 0,
            },
        ]

        # Filter by budget if provided
        if budget:
            budget_lower = budget.lower()
            if "low" in budget_lower or "budget" in budget_lower:
                flights = [f for f in flights if f["price"] < 800]
            elif "high" in budget_lower or "premium" in budget_lower:
                flights = [f for f in flights if f["price"] > 1000]

        result = {
            "from": from_loc,
            "to": to_location,
            "date": date,
            "flights": flights,
            "count": len(flights),
        }

        span.set_attribute("tool.result_count", len(flights))

        return result
