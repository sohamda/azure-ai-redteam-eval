"""Evaluator definitions — built-in, safety, and custom evaluators.

Uses the azure-ai-evaluation SDK to define which evaluators run during CE.
"""

from __future__ import annotations

import logging
from typing import Any

from azure.ai.evaluation import (
    CoherenceEvaluator,
    ContentSafetyEvaluator,
    FluencyEvaluator,
    GroundednessEvaluator,
    ProtectedMaterialEvaluator,
    RelevanceEvaluator,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom evaluator — demonstrates extensibility
# ---------------------------------------------------------------------------


class ConcisenessEvaluator:
    """Custom evaluator: checks whether the response is concise.

    Scores 1-5 where 5 = perfectly concise, 1 = excessively verbose.
    This is a simple heuristic demo — in production, use an LLM-as-judge.
    """

    def __init__(self) -> None:
        self.name = "conciseness"

    def __call__(self, *, response: str, **kwargs: Any) -> dict[str, float]:
        """Evaluate response conciseness based on length heuristics.

        Args:
            response: The agent response to evaluate.
            **kwargs: Additional arguments (ignored).

        Returns:
            Dict with 'conciseness' score (1-5).
        """
        word_count = len(response.split())

        if word_count <= 50:
            score = 5.0
        elif word_count <= 100:
            score = 4.5
        elif word_count <= 200:
            score = 4.0
        elif word_count <= 250:
            score = 3.0
        elif word_count <= 400:
            score = 2.5
        else:
            score = 2.0

        logger.debug("ConcisenessEvaluator: %d words → score %.1f", word_count, score)
        return {"conciseness": score}


# ---------------------------------------------------------------------------
# Evaluator registry
# ---------------------------------------------------------------------------


def get_builtin_evaluators(model_config: dict[str, str]) -> dict[str, Any]:
    """Get all built-in quality evaluators.

    Args:
        model_config: Azure OpenAI model configuration dict with
            'azure_endpoint', 'azure_deployment', 'api_version'.

    Returns:
        Dict mapping evaluator name to evaluator instance.
    """
    return {
        "groundedness": GroundednessEvaluator(model_config=model_config),
        "coherence": CoherenceEvaluator(model_config=model_config),
        "relevance": RelevanceEvaluator(model_config=model_config),
        "fluency": FluencyEvaluator(model_config=model_config),
    }


def get_safety_evaluators(azure_ai_project: dict[str, str], credential: Any = None) -> dict[str, Any]:
    """Get all safety evaluators.

    Args:
        azure_ai_project: AI Foundry project configuration dict with
            'subscription_id', 'resource_group_name', 'project_name'.
        credential: Azure credential (defaults to DefaultAzureCredential).

    Returns:
        Dict mapping evaluator name to evaluator instance.
    """
    if credential is None:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
    return {
        "content_safety": ContentSafetyEvaluator(credential=credential, azure_ai_project=azure_ai_project),
        "protected_material": ProtectedMaterialEvaluator(credential=credential, azure_ai_project=azure_ai_project),
    }


def get_custom_evaluators() -> dict[str, Any]:
    """Get all custom evaluators.

    Returns:
        Dict mapping evaluator name to evaluator instance.
    """
    return {
        "conciseness": ConcisenessEvaluator(),
    }


def get_all_evaluators(
    model_config: dict[str, str],
    azure_ai_project: dict[str, str] | Any,
) -> dict[str, Any]:
    """Get all evaluators (built-in + safety + custom).

    Args:
        model_config: Azure OpenAI model configuration.
        azure_ai_project: AI Foundry project configuration.

    Returns:
        Combined dict of all evaluator instances.
    """
    evaluators: dict[str, Any] = {}
    evaluators.update(get_builtin_evaluators(model_config))
    evaluators.update(get_safety_evaluators(azure_ai_project))
    evaluators.update(get_custom_evaluators())
    logger.info("Loaded %d evaluators: %s", len(evaluators), list(evaluators.keys()))
    return evaluators
