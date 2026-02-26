"""Eval plugin — triggers inline evaluation of agent responses.

Can be used by agents to self-assess response quality during execution.
Bridges the agent system into the CE loop.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def evaluate_response(query: str, response: str, context: str = "") -> dict[str, float]:
    """Run a quick inline evaluation of an agent response.

    In production, this calls the azure-ai-evaluation SDK.
    For the demo, returns mock scores to avoid blocking the agent flow.

    Args:
        query: The original user query.
        response: The agent's response to evaluate.
        context: Optional grounding context.

    Returns:
        Dict of evaluator names to scores (1-5 scale).
    """
    logger.info("Eval plugin invoked for query: %s", query[:80])

    # Mock scores for demo — in production, use azure-ai-evaluation SDK
    mock_scores: dict[str, float] = {
        "groundedness": 4.5,
        "coherence": 4.7,
        "relevance": 4.3,
        "fluency": 4.8,
        "safety": 5.0,
    }

    logger.info("Eval plugin scores: %s", mock_scores)
    return mock_scores
