"""Basic usage example of TravelOps Assistant."""

from app.agent import TravelOpsAgent
from app.config import get_config


def main():
    """Demonstrate basic TravelOps Assistant usage."""
    # Create agent using config from .env file (or defaults to stub)
    config = get_config()
    print(f"Using LLM Provider: {config.llm_provider}")
    print()
    agent = TravelOpsAgent(config)

    # Example 1: Simple trip planning
    print("Example 1: Simple Trip Planning")
    print("=" * 50)
    response = agent.run("Plan a 3-day trip to Paris")
    print(f"Assistant: {response.assistant_message}")
    print(f"Destination: {response.itinerary['destination']}")
    print(f"Dates: {response.itinerary['dates']}")
    print()

    # Example 2: With tool usage (weather)
    print("Example 2: Tool Usage (Weather)")
    print("=" * 50)
    response = agent.run("What's the weather like in Tokyo? Plan accordingly.")
    print(f"Assistant: {response.assistant_message}")
    print()

    # Example 3: With retrieval (KB query)
    print("Example 3: Knowledge Base Query")
    print("=" * 50)
    response = agent.run("What are the visa requirements for France?")
    print(f"Assistant: {response.assistant_message}")
    print()

    # Example 4: Multi-turn with memory
    print("Example 4: Multi-turn with Memory")
    print("=" * 50)
    session_id = "demo_session_123"

    response1 = agent.run("I prefer window seats", session_id=session_id)
    print(f"Turn 1: {response1.assistant_message}")

    response2 = agent.run("Book a flight to Paris", session_id=session_id)
    print(f"Turn 2: {response2.assistant_message}")
    print()

    # Example 5: Complex multi-step query
    print("Example 5: Complex Multi-step Query")
    print("=" * 50)
    response = agent.run(
        "Check weather, find hotels, and search for flights to Rome"
    )
    print(f"Assistant: {response.assistant_message}")
    print(f"Flights: {len(response.itinerary.get('flights', []))} found")
    print(f"Hotels: {len(response.itinerary.get('hotels', []))} found")
    print()


if __name__ == "__main__":
    main()
