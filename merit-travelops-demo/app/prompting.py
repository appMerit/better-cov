"""Prompt building and message assembly for TravelOps Assistant."""

import hashlib
import json
from typing import Any

from app.tracing import trace_operation


def build_messages(
    prompt: str,
    context_docs: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    session_memory: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Build message list for LLM."""
    with trace_operation(
        "travelops.prompt.build",
        {
            "has_context": context_docs is not None and len(context_docs) > 0,
            "has_tool_results": tool_results is not None and len(tool_results) > 0,
            "has_memory": session_memory is not None,
        },
    ) as span:
        messages = []

        # System prompt
        system_prompt = build_system_prompt()
        messages.append({"role": "system", "content": system_prompt})

        # Add context if available
        if context_docs:
            context_text = "\n\n".join(doc.get("content", "") for doc in context_docs)
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant knowledge base information:\n{context_text}",
                }
            )

        # Add session memory if available
        if session_memory and session_memory.get("preferences"):
            prefs_text = json.dumps(session_memory["preferences"], indent=2)
            messages.append(
                {"role": "system", "content": f"User preferences:\n{prefs_text}"}
            )

        # Add tool results if available
        if tool_results:
            for result in tool_results:
                tool_name = result.get("tool_name", "unknown")
                tool_output = result.get("output", "")
                messages.append(
                    {"role": "assistant", "content": f"Tool {tool_name} returned: {tool_output}"}
                )

        # User message
        messages.append({"role": "user", "content": prompt})

        # Set tracing attributes
        prompt_hash = hashlib.sha256(json.dumps(messages).encode()).hexdigest()[:16]
        span.set_attribute("prompt_hash", prompt_hash)
        span.set_attribute("message_count", len(messages))

        return messages


def build_system_prompt() -> str:
    """Build the system prompt."""
    return """You are TravelOps Assistant, a helpful travel planning AI.

Your role:
- Help users plan trips, find flights, hotels, and activities
- Provide accurate information based on provided context
- Create structured itineraries in JSON format
- Only use information from the provided knowledge base
- Call tools when needed (weather, hotel search, flight search)

Output format:
Always respond with valid JSON containing:
{
  "assistant_message": "Your natural language response",
  "itinerary": {
    "destination": {"city": "CityName", "country": "CountryName"},
    "dates": {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"},
    "flights": [],
    "hotels": [],
    "activities": [],
    "budget": null,
    "notes": ""
  }
}

Important policies:
- Never invent facts not in the provided context
- Always cite knowledge base when referencing policies or facts
- Use tools for real-time data (weather, availability)
- Respect user preferences from session memory
"""
