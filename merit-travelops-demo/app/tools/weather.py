"""Weather tool for getting current weather information."""

from typing import Any

from app.tracing import trace_operation


def get_weather(location: str, date: str | None = None) -> dict[str, Any]:
    """Get weather information for a location."""
    with trace_operation(
        "travelops.tool.call",
        {
            "tool.name": "get_weather",
            "tool.args": f'{{"location": "{location}", "date": "{date}"}}',
        },
    ) as span:
        # Stub implementation - returns deterministic weather
        weather_data = {
            "location": location,
            "date": date or "today",
            "temperature": 22,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 15,
        }

        # Add some variation based on location
        if "tokyo" in location.lower():
            weather_data["temperature"] = 28
            weather_data["humidity"] = 75
        elif "london" in location.lower():
            weather_data["temperature"] = 15
            weather_data["condition"] = "Rainy"

        span.set_attribute("tool.result_keys", str(list(weather_data.keys())))

        return weather_data
