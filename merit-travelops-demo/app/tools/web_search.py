"""Web search tool (stub implementation)."""

from typing import Any

from app.tracing import trace_operation


def web_search(query: str, num_results: int = 5) -> dict[str, Any]:
    """Perform web search (stub)."""
    with trace_operation(
        "travelops.tool.call",
        {
            "tool.name": "web_search",
            "tool.args": f'{{"query": "{query}", "num_results": {num_results}}}',
        },
    ) as span:
        # Stub implementation
        results = [
            {
                "title": f"Result {i + 1} for {query}",
                "url": f"https://example.com/result{i + 1}",
                "snippet": f"This is a search result snippet for {query}",
            }
            for i in range(num_results)
        ]

        result = {"query": query, "results": results, "count": len(results)}

        span.set_attribute("tool.result_count", len(results))

        return result
