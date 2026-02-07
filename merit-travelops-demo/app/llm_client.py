"""LLM client with stub and OpenAI implementations."""

import hashlib
import json
import time
from typing import Any

from app.config import Config


class StubLLMClient:
    """Deterministic stub LLM for testing without API keys."""

    def __init__(self, config: Config):
        self.config = config

    def generate(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Generate a deterministic response based on message hash."""
        # Create deterministic hash from messages
        message_str = json.dumps(messages, sort_keys=True)
        msg_hash = hashlib.sha256(message_str.encode()).hexdigest()[:8]

        # Check if this is a tool planning request
        if tools and any("tool" in str(msg).lower() for msg in messages):
            return self._generate_tool_call(messages, tools, msg_hash)

        # Extract key info from user message
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        user_lower = user_msg.lower()

        # Determine response based on content
        if "weather" in user_lower:
            city = self._extract_city(user_msg)
            return {
                "content": f"I'll check the weather for {city}.",
                "tool_calls": [
                    {
                        "name": "get_weather",
                        "args": {"location": city},
                    }
                ],
            }
        elif "hotel" in user_lower or "accommodation" in user_lower:
            city = self._extract_city(user_msg)
            return {
                "content": f"I'll search for hotels in {city}.",
                "tool_calls": [
                    {
                        "name": "search_hotels",
                        "args": {"location": city, "check_in": "2024-06-01", "check_out": "2024-06-05"},
                    }
                ],
            }
        elif "flight" in user_lower:
            return {
                "content": "I'll search for flights.",
                "tool_calls": [
                    {
                        "name": "search_flights",
                        "args": {"from": "New York", "to": "Paris", "date": "2024-06-01"},
                    }
                ],
            }
        else:
            # Generate itinerary response
            return self._generate_itinerary_response(user_msg, msg_hash)

    def _generate_itinerary_response(self, user_msg: str, msg_hash: str) -> dict[str, Any]:
        """Generate a complete itinerary response."""
        city = self._extract_city(user_msg)
        country = self._extract_country(user_msg)

        itinerary = {
            "destination": {"city": city, "country": country},
            "dates": {"start_date": "2024-06-01", "end_date": "2024-06-05"},
            "flights": [
                {
                    "departure": "New York",
                    "arrival": city,
                    "date": "2024-06-01",
                    "airline": "Air France",
                    "price": 850.0,
                }
            ],
            "hotels": [
                {
                    "name": f"{city} Grand Hotel",
                    "location": f"{city} City Center",
                    "check_in": "2024-06-01",
                    "check_out": "2024-06-05",
                    "price_per_night": 200.0,
                }
            ],
            "activities": [
                {"name": f"City Tour of {city}", "location": city, "date": "2024-06-02"},
                {"name": "Museum Visit", "location": city, "date": "2024-06-03"},
            ],
            "budget": 2500.0,
            "notes": f"Deterministic itinerary for {city} (hash: {msg_hash})",
        }

        assistant_message = (
            f"I've created a 4-day itinerary for {city}, {country}. "
            f"Your trip includes flights, hotel accommodation, and suggested activities."
        )

        return {"content": assistant_message, "itinerary": itinerary}

    def _generate_tool_call(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]], msg_hash: str
    ) -> dict[str, Any]:
        """Generate a tool call response."""
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Simple heuristic routing
        if "weather" in user_msg.lower():
            return {
                "content": None,
                "tool_calls": [{"name": "get_weather", "args": {"location": "Paris"}}],
            }
        elif "hotel" in user_msg.lower():
            return {
                "content": None,
                "tool_calls": [
                    {
                        "name": "search_hotels",
                        "args": {"location": "Paris", "check_in": "2024-06-01", "check_out": "2024-06-05"},
                    }
                ],
            }
        else:
            return {"content": "I'll help you with that.", "tool_calls": []}

    def _extract_city(self, text: str) -> str:
        """Extract city name from text (simple heuristic)."""
        cities = ["Paris", "London", "Tokyo", "New York", "Rome", "Barcelona", "Berlin", "Sydney"]
        for city in cities:
            if city.lower() in text.lower():
                return city
        return "Paris"  # default

    def _extract_country(self, text: str) -> str:
        """Extract country name from text (simple heuristic)."""
        countries = {
            "paris": "France",
            "london": "United Kingdom",
            "tokyo": "Japan",
            "new york": "USA",
            "rome": "Italy",
            "barcelona": "Spain",
            "berlin": "Germany",
            "sydney": "Australia",
        }
        text_lower = text.lower()
        for city, country in countries.items():
            if city in text_lower:
                return country
        return "France"  # default


class OpenAILLMClient:
    """OpenAI LLM client wrapper."""

    def __init__(self, config: Config):
        self.config = config
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=config.openai_api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")

    def generate(
        self, messages: list[dict[str, str]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Generate response using OpenAI API with JSON mode."""
        kwargs = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},  # Force JSON output
        }

        if tools:
            kwargs["tools"] = tools
            # Remove response_format when using tools (incompatible)
            kwargs.pop("response_format", None)

        # ===== TIMING INSTRUMENTATION START =====
        start_time = time.time()
        response = self.client.chat.completions.create(**kwargs)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Log timing to file
        try:
            with open('.merit/llm_timing.log', 'a') as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}|{kwargs['model']}|{duration_ms:.2f}ms|temp={self.config.temperature}|tools={bool(tools)}\n")
        except:
            pass  # Don't fail if logging fails
        # ===== TIMING INSTRUMENTATION END =====
        
        choice = response.choices[0]

        result = {"content": choice.message.content}

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {"name": tc.function.name, "args": json.loads(tc.function.arguments)}
                for tc in choice.message.tool_calls
            ]

        return result


def create_llm_client(config: Config | None = None) -> StubLLMClient | OpenAILLMClient:
    """Create appropriate LLM client based on configuration."""
    if config is None:
        from app.config import get_config

        config = get_config()

    if config.llm_provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OPENAI_API_KEY required when TRAVELOPS_LLM_PROVIDER=openai")
        return OpenAILLMClient(config)
    else:
        return StubLLMClient(config)
