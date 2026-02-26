"""Eval Metrics Exporter — exports CE scores as OTel metrics to App Insights.

Bridges Continuous Evaluation into Continuous Monitoring by making
evaluation scores visible as time-series custom metrics.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from opentelemetry import metrics

logger = logging.getLogger(__name__)


def get_eval_meter() -> metrics.Meter:
    """Get or create the evaluation metrics meter."""
    return metrics.get_meter("ce-eval-metrics")


def export_eval_scores(
    scores: dict[str, float],
    evaluation_name: str = "ce-evaluation",
    run_id: str = "",
) -> None:
    """Export evaluation scores as OpenTelemetry custom metrics.

    Each evaluator score becomes a custom metric in Application Insights,
    enabling dashboard visualization of CE trends over time.

    Args:
        scores: Dict mapping evaluator name to score (1-5 scale).
        evaluation_name: Name of the evaluation run.
        run_id: Unique identifier for the evaluation run.
    """
    meter = get_eval_meter()
    timestamp = datetime.now(tz=UTC).isoformat()

    for evaluator, score in scores.items():
        # Create a histogram to track score distribution over time
        histogram = meter.create_histogram(
            name=f"ce.score.{evaluator}",
            description=f"Continuous Evaluation score for {evaluator}",
            unit="score",
        )

        attributes = {
            "evaluator": evaluator,
            "evaluation_name": evaluation_name,
            "run_id": run_id,
            "timestamp": timestamp,
        }

        histogram.record(score, attributes=attributes)
        logger.info("Exported metric ce.score.%s = %.2f", evaluator, score)

    # Also export an aggregate score
    if scores:
        avg_score = sum(scores.values()) / len(scores)
        avg_histogram = meter.create_histogram(
            name="ce.score.average",
            description="Average Continuous Evaluation score across all evaluators",
            unit="score",
        )
        avg_histogram.record(avg_score, attributes={
            "evaluation_name": evaluation_name,
            "run_id": run_id,
            "timestamp": timestamp,
        })
        logger.info("Exported ce.score.average = %.2f", avg_score)

    logger.info("Exported %d evaluation metrics to App Insights", len(scores) + 1)


def export_redteam_metrics(
    category_results: dict[str, dict[str, int]],
    run_id: str = "",
) -> None:
    """Export red-team results as OTel metrics.

    Args:
        category_results: Dict mapping category to {total, passed, failed} counts.
        run_id: Unique identifier for the red-team run.
    """
    meter = get_eval_meter()

    for category, counts in category_results.items():
        counter = meter.create_counter(
            name=f"ce.redteam.{category}",
            description=f"Red team probe results for {category}",
            unit="probes",
        )

        counter.add(counts.get("passed", 0), attributes={
            "category": category,
            "result": "passed",
            "run_id": run_id,
        })
        counter.add(counts.get("failed", 0), attributes={
            "category": category,
            "result": "failed",
            "run_id": run_id,
        })

    logger.info("Exported red-team metrics for %d categories", len(category_results))
