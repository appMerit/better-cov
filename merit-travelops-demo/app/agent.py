"""Main TravelOps Agent orchestration logic."""

import uuid
from typing import Any

from app.config import Config, get_config
from app.llm_client import create_llm_client
from app.postprocess import normalize_itinerary, parse_llm_response
from app.prompting import build_messages
from app.retrieval import retrieve
from app.router import route
from app.schemas import TravelOpsResponse
from app.state import load_session, update_session_memory
from app.tools import get_weather, search_flights, search_hotels
from app.tracing import trace_operation


class TravelOpsAgent:
    """Main agent class for TravelOps Assistant."""

    def __init__(self, config: Config | None = None):
        self.config = config or get_config()
        self.llm_client = create_llm_client(self.config)

    def run(self, prompt: str, session_id: str | None = None) -> TravelOpsResponse:
        """Run the agent on a prompt."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        with trace_operation(
            "travelops.agent.run",
            {
                "session_id": session_id,
                "prompt_length": len(prompt),
            },
        ):
            # Load session memory
            session_memory = None
            if self.config.enable_memory:
                session_memory = load_session(session_id)

            # Route the request
            routing_decision = {}
            if self.config.enable_routing:
                routing_decision = route(prompt, session_memory)

            # Retrieve context if needed
            context_docs = None
            if self.config.enable_retrieval and routing_decision.get("needs_retrieval", False):
                context_docs = retrieve(prompt)

            # Execute tools if needed
            tool_results = None
            if routing_decision.get("needs_tools", False):
                tool_results = self._execute_tools(routing_decision["tools"], prompt)

            # Build messages
            messages = build_messages(prompt, context_docs, tool_results, session_memory)

            # Generate response
            with trace_operation(
                "travelops.llm.generate",
                {
                    "llm.provider": self.config.llm_provider,
                    "llm.temperature": self.config.temperature,
                },
            ):
                llm_response = self.llm_client.generate(messages)

            # Parse and normalize response
            assistant_message, raw_itinerary = parse_llm_response(llm_response)

            if raw_itinerary:
                itinerary = normalize_itinerary(raw_itinerary)
            else:
                # Create minimal itinerary
                itinerary = {
                    "destination": {"city": "Unknown", "country": "Unknown"},
                    "dates": {"start_date": "2024-01-01", "end_date": "2024-01-01"},
                    "flights": [],
                    "hotels": [],
                    "activities": [],
                    "budget": None,
                    "notes": assistant_message,
                }

            # Create response
            response = TravelOpsResponse(
                assistant_message=assistant_message,
                itinerary=itinerary,
                session_id=session_id,
            )

            # Update session memory
            if self.config.enable_memory:
                update_session_memory(session_id, prompt, response.model_dump())

            return response

    def _execute_tools(self, tool_names: list[str], prompt: str) -> list[dict[str, Any]]:
        """Execute specified tools."""
        results = []

        for tool_name in tool_names:
            try:
                if tool_name == "get_weather":
                    location = self._extract_location(prompt)
                    result = get_weather(location)
                    results.append({"tool_name": "get_weather", "output": str(result)})

                elif tool_name == "search_hotels":
                    location = self._extract_location(prompt)
                    result = search_hotels(
                        location, check_in="2024-06-01", check_out="2024-06-05"
                    )
                    results.append({"tool_name": "search_hotels", "output": str(result)})

                elif tool_name == "search_flights":
                    location = self._extract_location(prompt)
                    result = search_flights(
                        from_location="New York", to_location=location, date="2024-06-01"
                    )
                    results.append({"tool_name": "search_flights", "output": str(result)})

            except Exception as e:
                # Log error but continue
                results.append({"tool_name": tool_name, "output": f"Error: {str(e)}"})

        return results

    def _extract_location(self, text: str) -> str:
        """Extract location from text (simple heuristic)."""
        cities = ["Paris", "London", "Tokyo", "New York", "Rome", "Barcelona", "Berlin", "Sydney"]
        for city in cities:
            if city.lower() in text.lower():
                return city
        return "Paris"  # default

    def should_stop(self, step: int) -> tuple[bool, str]:
        """Determine if agent should stop iterating."""
        with trace_operation(
            "travelops.agent.should_stop",
            {
                "agent.steps": step,
                "max_steps": self.config.max_agent_steps,
            },
        ) as span:
            if step >= self.config.max_agent_steps:
                span.set_attribute("termination.reason", "max_steps_reached")
                return True, "max_steps_reached"

            span.set_attribute("termination.reason", "continue")
            return False, "continue"


def create_agent(config: Config | None = None) -> TravelOpsAgent:
    """Create a TravelOps agent instance."""
    return TravelOpsAgent(config)
