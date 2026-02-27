"""Score Tracker — pushes eval scores as App Insights custom metrics.

Bridges Continuous Evaluation into Continuous Monitoring by making
evaluation scores visible as time-series metrics in Application Insights.

IMPORTANT: Metric names use the ``ce.score.{evaluator}`` prefix so they
match the Workbook / Dashboard KQL queries. Do **not** change the prefix
without updating ``ce_cm_dashboard.json`` as well.
"""

from __future__ import annotations

import logging

from opentelemetry import metrics

from src.config import get_settings

logger = logging.getLogger(__name__)

# Lazy-initialized meter. We must NOT create it at module-level because
# setup_telemetry() (which configures the Azure Monitor MeterProvider) may
# not have run yet at import time.
_meter: metrics.Meter | None = None


def _get_meter() -> metrics.Meter:
    """Return the score-tracker meter, creating it on first call."""
    global _meter  # noqa: PLW0603
    if _meter is None:
        _meter = metrics.get_meter("ce-score-tracker")
    return _meter


def track_scores(scores: dict[str, float], run_id: str = "") -> None:
    """Push evaluation scores as OpenTelemetry metrics to Application Insights.

    Each score is emitted as a histogram record with the evaluator name.
    These metrics appear in App Insights ``customMetrics`` table and can be
    visualised in the CE/CM dashboard workbook.

    The metric name follows the pattern ``ce.score.{evaluator}`` which is
    the same prefix used by :func:`eval_metrics_exporter.export_eval_scores`
    and expected by the workbook queries.

    Args:
        scores: Dict mapping evaluator name to score (1-5 scale).
        run_id: Optional evaluation run identifier for correlation.
    """
    settings = get_settings()
    meter = _get_meter()

    for evaluator, score in scores.items():
        metric_name = f"ce.score.{evaluator}"
        histogram = meter.create_histogram(
            name=metric_name,
            description=f"CE evaluation score for {evaluator}",
            unit="score",
        )

        attributes: dict[str, str] = {
            "evaluator": evaluator,
            "run_id": run_id,
            "project": settings.ai_foundry.project,
        }

        histogram.record(score, attributes=attributes)
        logger.info("Tracked metric %s = %.2f (run: %s)", metric_name, score, run_id)

    # Also publish an aggregate average
    if scores:
        avg_score = sum(scores.values()) / len(scores)
        avg_histogram = meter.create_histogram(
            name="ce.score.average",
            description="Average CE score across all evaluators",
            unit="score",
        )
        avg_histogram.record(avg_score, attributes={
            "run_id": run_id,
            "project": settings.ai_foundry.project,
        })
        logger.info("Tracked ce.score.average = %.2f", avg_score)

    logger.info("All %d scores tracked as custom metrics (ce.score.* prefix)", len(scores))
