"""Knowledge base retrieval for TravelOps Assistant."""

from typing import Any

from app.tracing import trace_operation


# Simple in-memory knowledge base
KB_DOCUMENTS = [
    {
        "id": "visa_france",
        "content": "France visa requirements: US citizens can visit France for up to 90 days without a visa for tourism.",
        "keywords": ["visa", "france", "requirements"],
    },
    {
        "id": "visa_japan",
        "content": "Japan visa requirements: US citizens can visit Japan for up to 90 days without a visa for tourism.",
        "keywords": ["visa", "japan", "requirements"],
    },
    {
        "id": "tipping_france",
        "content": "Tipping in France: Service charge is included in restaurant bills. Additional tipping of 5-10% is appreciated for good service.",
        "keywords": ["tipping", "france", "restaurant"],
    },
    {
        "id": "tipping_japan",
        "content": "Tipping in Japan: Tipping is not customary and may be considered rude. Service charges are included in bills.",
        "keywords": ["tipping", "japan", "culture"],
    },
    {
        "id": "weather_paris",
        "content": "Paris weather: Mild temperatures year-round. Summer (June-August) averages 20-25°C. Bring an umbrella as rain is common.",
        "keywords": ["weather", "paris", "climate"],
    },
    {
        "id": "weather_tokyo",
        "content": "Tokyo weather: Humid summers (June-August) with temperatures 25-35°C. Spring (March-May) is ideal for cherry blossoms.",
        "keywords": ["weather", "tokyo", "climate"],
    },
    {
        "id": "budget_paris",
        "content": "Paris budget: Expect $150-200/day for mid-range travel including accommodation, meals, and activities.",
        "keywords": ["budget", "paris", "cost"],
    },
    {
        "id": "budget_tokyo",
        "content": "Tokyo budget: Expect $120-180/day for mid-range travel including accommodation, meals, and activities.",
        "keywords": ["budget", "tokyo", "cost"],
    },
    {
        "id": "transport_paris",
        "content": "Paris transportation: Metro and bus system is extensive and affordable. Consider a multi-day pass for convenience.",
        "keywords": ["transport", "paris", "metro"],
    },
    {
        "id": "transport_tokyo",
        "content": "Tokyo transportation: JR Pass offers unlimited train travel. Tokyo Metro and JR lines cover the entire city.",
        "keywords": ["transport", "tokyo", "train"],
    },
]


def retrieve(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """Retrieve relevant documents from knowledge base."""
    with trace_operation(
        "travelops.retrieval",
        {
            "query_length": len(query),
            "top_k": top_k,
        },
    ) as span:
        # Simple keyword-based retrieval
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Score documents based on keyword overlap
        scored_docs = []
        for doc in KB_DOCUMENTS:
            score = 0
            for keyword in doc["keywords"]:
                if keyword in query_lower:
                    score += 2
            # Also check content
            content_words = set(doc["content"].lower().split())
            overlap = len(query_words & content_words)
            score += overlap * 0.1

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score and return top_k
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        results = [doc for score, doc in scored_docs[:top_k]]

        # Set trace attributes
        doc_ids = [doc["id"] for doc in results]
        scores = [score for score, _ in scored_docs[:top_k]]

        span.set_attribute("retrieval.doc_ids", str(doc_ids))
        span.set_attribute("retrieval.scores", str(scores))
        span.set_attribute("retrieval.num_results", len(results))

        return results
