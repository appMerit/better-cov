"""Session state and memory management."""

from typing import Any

from app.tracing import trace_operation

# In-memory session store
_SESSION_STORE: dict[str, dict[str, Any]] = {}


def load_session(session_id: str) -> dict[str, Any]:
    """Load session data from store."""
    with trace_operation("travelops.state.load", {"session_id": session_id}) as span:
        session_data = _SESSION_STORE.get(session_id, {"preferences": {}, "history": []})
        span.set_attribute("has_preferences", len(session_data.get("preferences", {})) > 0)
        span.set_attribute("history_length", len(session_data.get("history", [])))
        return session_data


def save_session(session_id: str, session_data: dict[str, Any]) -> None:
    """Save session data to store."""
    with trace_operation("travelops.state.save", {"session_id": session_id}) as span:
        _SESSION_STORE[session_id] = session_data
        span.set_attribute("preferences_count", len(session_data.get("preferences", {})))
        span.set_attribute("history_length", len(session_data.get("history", [])))


def update_session_memory(
    session_id: str, prompt: str, response: dict[str, Any], extract_preferences: bool = True
) -> None:
    """Update session memory with new interaction."""
    session_data = load_session(session_id)

    # Add to history
    session_data.setdefault("history", []).append(
        {"prompt": prompt, "response": response.get("assistant_message", "")}
    )

    # Extract preferences (simple heuristic)
    if extract_preferences:
        prompt_lower = prompt.lower()
        prefs = session_data.setdefault("preferences", {})

        if "budget" in prompt_lower:
            # Try to extract budget
            words = prompt.split()
            for i, word in enumerate(words):
                if word.startswith("$") and i + 1 < len(words):
                    try:
                        amount = float(words[i].replace("$", "").replace(",", ""))
                        prefs["budget"] = amount
                    except ValueError:
                        pass

        if "prefer" in prompt_lower or "like" in prompt_lower:
            if "window seat" in prompt_lower:
                prefs["seat_preference"] = "window"
            elif "aisle seat" in prompt_lower:
                prefs["seat_preference"] = "aisle"

    save_session(session_id, session_data)


def clear_all_sessions() -> None:
    """Clear all session data (for testing)."""
    _SESSION_STORE.clear()
