"""Search plugin — provides web/document search capabilities to agents.

This plugin can be registered with any Executor to give it search tool access.
Kept simple for the demo; in production, this would call Azure AI Search.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def search(query: str, top_k: int = 3) -> list[dict[str, str]]:
    """Search for relevant documents given a query.

    In production, this would call Azure AI Search or Azure Cognitive Search.
    For the demo, returns mock results to keep the demo self-contained.

    Args:
        query: The search query string.
        top_k: Number of results to return.

    Returns:
        List of search result dicts with 'title', 'content', and 'source' keys.
    """
    logger.info("Search plugin invoked: query=%s, top_k=%d", query[:80], top_k)

    # Mock results for demo — replace with Azure AI Search in production
    mock_results = [
        {
            "title": "Azure AI Best Practices",
            "content": (
                "When deploying AI applications to Azure, use managed identity for authentication, "
                "enable Application Insights for observability, and implement continuous evaluation "
                "to monitor model quality over time."
            ),
            "source": "https://learn.microsoft.com/azure/ai-services/",
        },
        {
            "title": "Continuous Evaluation for GenAI",
            "content": (
                "Continuous Evaluation (CE) ensures every code change and deployment is automatically "
                "evaluated for AI quality. Use golden datasets, built-in evaluators (groundedness, "
                "coherence, relevance), and threshold gating to prevent regressions."
            ),
            "source": "https://learn.microsoft.com/azure/ai-studio/evaluation",
        },
        {
            "title": "Red Teaming AI Systems",
            "content": (
                "AI red teaming uses adversarial probes — prompt injection, jailbreak attempts, "
                "PII extraction — to stress-test AI systems before they reach production."
            ),
            "source": "https://learn.microsoft.com/azure/ai-services/openai/red-teaming",
        },
    ]
    return mock_results[:top_k]
