"""Merit tests for grounding enforcement (Cluster 4)."""

from merit import Case, iter_cases, resource, sut
from merit.predicates import has_unsupported_facts

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.kb_docs import EXPECTED_KB_FACTS
from tests.fixtures.scenarios import generate_grounding_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_grounding_cases())
async def merit_grounding_enforcement(case: Case, travel_ops_sut):
    """Test that responses are grounded in provided context."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Build context from all KB facts
    kb_context = " ".join(EXPECTED_KB_FACTS.values())

    # Check that response doesn't contain unsupported facts
    response_text = f"{response.assistant_message} {response.itinerary.get('notes', '')}"

    # Use Merit's has_unsupported_facts predicate
    has_hallucinations = await has_unsupported_facts(response_text, kb_context)

    assert not has_hallucinations, (
        f"Response contains unsupported facts (hallucination). "
        f"Response: {response_text[:300]}"
    )

    # For queries requiring KB context
    if case.references.get("context_required", False):
        # Response should not be generic - should reference specific facts
        generic_phrases = [
            "i don't have",
            "i cannot provide",
            "i'm not sure",
            "i don't know",
            "unable to answer",
        ]

        response_lower = response_text.lower()
        has_generic = any(phrase in response_lower for phrase in generic_phrases)

        # If it's generic, it should at least acknowledge the limitation
        if has_generic:
            assert (
                "knowledge base" in response_lower or "provided information" in response_lower
            ), "Generic response should reference knowledge base limitations"
