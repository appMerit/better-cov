"""Merit tests for retrieval relevance (Cluster 3)."""

from merit import Case, iter_cases, resource, sut
from merit.predicates import has_facts

from app.agent import TravelOpsAgent
from app.config import get_config
from tests.faults.patchers import apply_faults_via_config
from tests.fixtures.scenarios import generate_retrieval_cases


@sut
class TravelOpsSUT:
    """SUT wrapper for TravelOps agent (enables Merit tracking and tracing)."""
    def __init__(self):
        config = get_config()
        self.agent = TravelOpsAgent(config)
        self.agent = apply_faults_via_config(self.agent)
    
    def __call__(self, prompt: str, session_id: str | None = None):
        return self.agent.run(prompt, session_id=session_id)


@iter_cases(generate_retrieval_cases())
async def merit_retrieval_relevance(case: Case, travel_ops_sut):
    """Test that retrieval returns relevant documents."""
    # Run the agent through SUT wrapper (enables Merit tracking)
    response = travel_ops_sut(**case.sut_input_values)

    # Check if retrieval was invoked (when it should be)
    if case.references.get("kb_doc_id"):
        # Check that response semantically contains the required fact from KB
        required_fact = case.references.get("required_fact", "")
        response_text = f"{response.assistant_message} {response.itinerary.get('notes', '')}"

        # Use semantic similarity with lenient matching (strict=False)
        # Capture the result to access reasoning
        result = await has_facts(response_text, required_fact, strict=False)
        
        # Assert with detailed reasoning from the predicate
        assert result, (
            f"Response missing required fact '{required_fact}' from KB.\n"
            f"Predicate reasoning: {result.message}\n"
            f"Confidence: {result.confidence}\n"
            f"Response: {response_text[:200]}"
        )

    # For multi-fact queries
    if "required_facts" in case.references:
        response_text = f"{response.assistant_message} {response.itinerary.get('notes', '')}"

        for fact in case.references["required_facts"]:
            # Use semantic similarity with lenient matching
            result = await has_facts(response_text, fact, strict=False)
            assert result, (
                f"Response missing required fact '{fact}' from KB.\n"
                f"Predicate reasoning: {result.message}\n"
                f"Confidence: {result.confidence}"
            )

    # Response should not be empty
    assert (
        len(response.assistant_message) > 0
    ), "Response assistant_message should not be empty"
