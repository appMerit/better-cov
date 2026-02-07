"""Request router to determine if tools or retrieval are needed."""

from typing import Any

from app.tracing import trace_operation


def route(prompt: str, session_memory: dict[str, Any] | None = None) -> dict[str, Any]:
    """Determine routing decision for the request."""
    with trace_operation("travelops.route", {"prompt_length": len(prompt)}) as span:
        prompt_lower = prompt.lower()

        # Determine if we need tools
        needs_weather = "weather" in prompt_lower
        needs_hotels = "hotel" in prompt_lower or "accommodation" in prompt_lower
        needs_flights = "flight" in prompt_lower

        # Determine if we need retrieval
        needs_retrieval = any(
            keyword in prompt_lower
            for keyword in [
                "visa",
                "tipping",
                "culture",
                "budget",
                "policy",
                "requirement",
                "custom",
            ]
        )

        tools_needed = []
        if needs_weather:
            tools_needed.append("get_weather")
        if needs_hotels:
            tools_needed.append("search_hotels")
        if needs_flights:
            tools_needed.append("search_flights")

        routing_decision = {
            "needs_retrieval": needs_retrieval,
            "needs_tools": len(tools_needed) > 0,
            "tools": tools_needed,
            "can_answer_directly": not needs_retrieval and not tools_needed,
        }

        # Set trace attributes
        span.set_attribute("route.needs_retrieval", needs_retrieval)
        span.set_attribute("route.needs_tools", len(tools_needed) > 0)
        span.set_attribute("route.tools", str(tools_needed))

        return routing_decision
