"""Full Continuous Evaluation entry point.

Loads the golden dataset, runs all evaluators via azure-ai-evaluation,
applies thresholds, and outputs results. Callable from CLI and CI.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from azure.ai.evaluation import AzureAIProject, evaluate
from azure.identity import DefaultAzureCredential

from src.config import get_settings
from src.continuous_evaluation.evaluators import get_all_evaluators
from src.continuous_evaluation.metrics import format_results_table, summarize_scores
from src.continuous_evaluation.retry import retry_with_backoff
from src.continuous_evaluation.thresholds import any_failures, check_all_thresholds
from src.continuous_monitoring.eval_metrics_exporter import export_eval_scores
from src.continuous_monitoring.telemetry import flush_telemetry, setup_telemetry

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).parent / "datasets" / "eval_golden.jsonl"
RESULTS_OUTPUT = Path("evaluation_results.json")


def _get_model_config() -> dict[str, str]:
    """Build the model config dict for azure-ai-evaluation evaluators."""
    settings = get_settings()
    return {
        "azure_endpoint": settings.openai.endpoint,
        "azure_deployment": settings.openai.deployment,
        "api_version": settings.openai.api_version,
    }


def _get_azure_ai_project() -> AzureAIProject:
    """Build the Azure AI project config for safety evaluators."""
    settings = get_settings()
    return AzureAIProject(
        subscription_id=settings.azure.subscription_id,
        resource_group_name=settings.azure.resource_group,
        project_name=settings.ai_foundry.project,
    )


async def run_full_evaluation() -> dict[str, float]:
    """Run the full Continuous Evaluation against the golden dataset.

    Returns:
        Dict of aggregated evaluator scores.

    Raises:
        SystemExit: If any evaluator score falls below its threshold.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    # Initialize telemetry so eval scores flow to App Insights
    setup_telemetry()

    logger.info("=" * 60)
    logger.info("CONTINUOUS EVALUATION — Full Run")
    logger.info("=" * 60)

    if not DATASET_PATH.exists():
        logger.error("Golden dataset not found: %s", DATASET_PATH)
        sys.exit(1)

    model_config = _get_model_config()
    azure_ai_project = _get_azure_ai_project()

    logger.info("Loading evaluators...")
    evaluators = get_all_evaluators(model_config, azure_ai_project)

    logger.info("Running evaluation against: %s", DATASET_PATH)
    DefaultAzureCredential()

    results = retry_with_backoff(
        evaluate,
        data=str(DATASET_PATH),
        evaluators=evaluators,
        azure_ai_project=azure_ai_project,
        evaluation_name="ce-full-evaluation",
        max_retries=3,
        base_delay=15.0,
    )

    # Summarize scores
    scores = summarize_scores(results)
    logger.info("\n%s", format_results_table(scores))

    # Export scores as custom metrics to App Insights (CE → CM bridge)
    export_eval_scores(scores, evaluation_name="ce-full-evaluation")
    logger.info("Eval scores exported to App Insights")

    # Save results
    with RESULTS_OUTPUT.open("w") as f:
        json.dump({"scores": scores, "raw_results": str(results)}, f, indent=2)
    logger.info("Results saved to %s", RESULTS_OUTPUT)

    # Check thresholds
    threshold_results = check_all_thresholds(scores)
    logger.info("\nThreshold Check:")
    for tr in threshold_results:
        logger.info("  %s: %.2f (threshold: %.2f) → %s", tr.evaluator, tr.score, tr.threshold, tr.status.value)

    if any_failures(threshold_results):
        logger.error("EVALUATION FAILED — scores below thresholds. Deployment blocked.")
        flush_telemetry(timeout_millis=15_000)
        sys.exit(1)

    logger.info("EVALUATION PASSED — all scores meet thresholds.")
    flush_telemetry(timeout_millis=15_000)
    return scores


def main() -> None:
    """CLI entry point for `python -m src.continuous_evaluation.run_evaluation`."""
    asyncio.run(run_full_evaluation())


if __name__ == "__main__":
    main()
