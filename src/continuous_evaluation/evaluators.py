"""Evaluator definitions — built-in, safety, and custom evaluators.

Uses the azure-ai-evaluation SDK to define which evaluators run during CE.
"""

from __future__ import annotations

import json
import logging
import re
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
# Custom evaluator — demonstrates extensibility (LLM-as-judge)
# ---------------------------------------------------------------------------

CONCISENESS_JUDGE_PROMPT = """You are an expert evaluator scoring the CONCISENESS of an AI assistant's answer.

Conciseness measures whether the response delivers the necessary information without \
redundancy, padding, hedging, or filler — while still being complete. A short answer that \
omits required information is NOT concise; it is incomplete.

Score on an integer 1-5 scale:
5 = Perfectly concise: every sentence earns its place, no fluff, nothing missing.
4 = Mostly concise: minor redundancy or a little padding.
3 = Adequate: noticeable repetition or over-explanation.
2 = Verbose: significant redundancy; the answer is buried.
1 = Extremely verbose: mostly noise, or padded to obscure a thin answer.

Return ONLY a JSON object, no prose:
{{"score": <integer 1-5>, "reason": "<one short sentence>"}}

[User query]
{query}

[Assistant response]
{response}
"""


class ConcisenessEvaluator:
    """Custom evaluator: scores whether a response is concise (1-5).

    Prefers an **LLM-as-judge** when a ``model_config`` is supplied (the same
    Azure OpenAI deployment used by the built-in evaluators). Falls back to a
    fast word-count heuristic when no model is configured or the judge call
    fails — so unit tests and offline demos always produce a score.
    """

    def __init__(self, model_config: dict[str, str] | None = None) -> None:
        self.name = "conciseness"
        self._model_config = model_config

    def __call__(self, *, response: str, query: str = "", **kwargs: Any) -> dict[str, float]:
        """Evaluate response conciseness.

        Args:
            response: The agent response to evaluate.
            query: The originating user query (used by the LLM judge for context).
            **kwargs: Additional dataset columns (ignored).

        Returns:
            Dict with 'conciseness' score (1-5).
        """
        if self._model_config:
            score = self._llm_judge(query=query, response=response)
            if score is not None:
                return {"conciseness": score}
            logger.warning("Conciseness LLM judge unavailable — using heuristic fallback")
        return {"conciseness": self._heuristic(response)}

    def _llm_judge(self, *, query: str, response: str) -> float | None:
        """Score conciseness with an LLM judge. Returns None on any failure."""
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            from openai import AzureOpenAI

            cfg = self._model_config or {}
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            client = AzureOpenAI(
                azure_endpoint=cfg["azure_endpoint"],
                azure_ad_token_provider=token_provider,
                api_version=cfg.get("api_version", "2024-12-01-preview"),
            )
            completion = client.chat.completions.create(
                model=cfg["azure_deployment"],
                messages=[
                    {"role": "system", "content": "You are a strict, consistent evaluation judge."},
                    {"role": "user", "content": CONCISENESS_JUDGE_PROMPT.format(query=query, response=response)},
                ],
                temperature=0.0,
                max_tokens=120,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content or "{}"
            score = float(json.loads(raw).get("score"))
            return max(1.0, min(5.0, score))
        except Exception as e:  # noqa: BLE001 — judge must never break the eval run
            logger.debug("Conciseness LLM judge failed: %s", e)
            return None

    @staticmethod
    def _heuristic(response: str) -> float:
        """Length-based conciseness fallback when no LLM judge is available."""
        word_count = len(re.findall(r"\S+", response))

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

        logger.debug("ConcisenessEvaluator heuristic: %d words → score %.1f", word_count, score)
        return score


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


def get_custom_evaluators(model_config: dict[str, str] | None = None) -> dict[str, Any]:
    """Get all custom evaluators.

    Args:
        model_config: Azure OpenAI model configuration. When provided, custom
            evaluators that support LLM-as-judge use this deployment; otherwise
            they fall back to heuristics.

    Returns:
        Dict mapping evaluator name to evaluator instance.
    """
    return {
        "conciseness": ConcisenessEvaluator(model_config=model_config),
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
    evaluators.update(get_custom_evaluators(model_config))
    logger.info("Loaded %d evaluators: %s", len(evaluators), list(evaluators.keys()))
    return evaluators
