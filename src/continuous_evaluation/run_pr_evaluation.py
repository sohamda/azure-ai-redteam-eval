"""Lightweight PR Evaluation — fast 5-row eval for CI.

Runs a subset of evaluators against a small dataset for quick feedback.
Outputs results to stdout for $GITHUB_STEP_SUMMARY.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from azure.ai.evaluation import AzureAIProject, evaluate

from src.config import get_settings
from src.continuous_evaluation.evaluators import get_builtin_evaluators, get_custom_evaluators
from src.continuous_evaluation.metrics import format_results_table, summarize_scores
from src.continuous_evaluation.thresholds import any_failures, check_all_thresholds

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "datasets" / "eval_golden_small.jsonl"


def _get_model_config() -> dict[str, str]:
    """Build the model config dict for evaluators."""
    settings = get_settings()
    return {
        "azure_endpoint": settings.openai.endpoint,
        "azure_deployment": settings.openai.deployment,
        "api_version": settings.openai.api_version,
    }


async def run_pr_evaluation() -> dict[str, float]:
    """Run lightweight evaluation for PR gating.

    Uses only built-in + custom evaluators (no safety — too slow for PR) against
    a small 5-row dataset. Designed to finish in < 60 seconds.

    Returns:
        Dict of aggregated evaluator scores.

    Raises:
        SystemExit: If any evaluator score falls below its threshold.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    logger.info("=" * 60)
    logger.info("CONTINUOUS EVALUATION — PR Lightweight Run")
    logger.info("=" * 60)

    if not DATASET_PATH.exists():
        logger.error("PR dataset not found: %s", DATASET_PATH)
        sys.exit(1)

    model_config = _get_model_config()
    settings = get_settings()
    azure_ai_project = AzureAIProject(
        subscription_id=settings.azure.subscription_id,
        resource_group_name=settings.azure.resource_group,
        project_name=settings.ai_foundry.project,
    )

    # Only built-in + custom evaluators for speed
    evaluators = {**get_builtin_evaluators(model_config), **get_custom_evaluators()}
    logger.info("Running PR eval with %d evaluators against %s", len(evaluators), DATASET_PATH)

    results = evaluate(
        data=str(DATASET_PATH),
        evaluators=evaluators,
        azure_ai_project=azure_ai_project,
        evaluation_name="ce-pr-evaluation",
    )

    scores = summarize_scores(results)

    # Output for $GITHUB_STEP_SUMMARY
    table = format_results_table(scores)
    print("\n## Continuous Evaluation — PR Results\n")
    print(table)

    # Check thresholds
    threshold_results = check_all_thresholds(scores)
    if any_failures(threshold_results):
        print("\n**EVALUATION FAILED** — scores below thresholds.")
        sys.exit(1)

    print("\n**EVALUATION PASSED** — all scores meet thresholds.")
    return scores


def main() -> None:
    """CLI entry point for `python -m src.continuous_evaluation.run_pr_evaluation`."""
    asyncio.run(run_pr_evaluation())


if __name__ == "__main__":
    main()
