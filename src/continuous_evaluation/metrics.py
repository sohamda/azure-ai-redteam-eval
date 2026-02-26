"""Metrics — parse and format evaluation results into readable tables.

Utility functions shared by run_evaluation.py and run_pr_evaluation.py.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def summarize_scores(results: Any) -> dict[str, float]:
    """Extract aggregated scores from azure-ai-evaluation results.

    The evaluate() function returns a result object with metrics.
    This function extracts the mean scores per evaluator.

    Args:
        results: The result object from azure.ai.evaluation.evaluate().

    Returns:
        Dict mapping evaluator name to mean score.
    """
    scores: dict[str, float] = {}

    # The results object has a 'metrics' dict with keys like 'groundedness.groundedness'
    if hasattr(results, "metrics"):
        metrics_dict = results.metrics
    elif isinstance(results, dict) and "metrics" in results:
        metrics_dict = results["metrics"]
    else:
        logger.warning("Unexpected results format: %s", type(results))
        return scores

    for key, value in metrics_dict.items():
        # Keys are like 'groundedness.groundedness', 'coherence.coherence', etc.
        # Extract the short evaluator name
        parts = key.split(".")
        evaluator_name = parts[-1] if parts else key

        if isinstance(value, (int, float)):
            scores[evaluator_name] = float(value)

    logger.info("Summarized %d evaluator scores", len(scores))
    return scores


def format_results_table(scores: dict[str, float]) -> str:
    """Format evaluation scores as a markdown table.

    Args:
        scores: Dict mapping evaluator name to score.

    Returns:
        Markdown table string suitable for $GITHUB_STEP_SUMMARY.
    """
    lines = [
        "| Evaluator | Score |",
        "|-----------|-------|",
    ]

    for evaluator, score in sorted(scores.items()):
        emoji = "✅" if score >= 4.0 else "⚠️" if score >= 3.0 else "❌"
        lines.append(f"| {evaluator} | {emoji} {score:.2f} |")

    # Add average
    if scores:
        avg = sum(scores.values()) / len(scores)
        lines.append(f"| **Average** | **{avg:.2f}** |")

    return "\n".join(lines)
