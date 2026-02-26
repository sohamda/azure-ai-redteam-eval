"""Score Tracker — pushes eval scores as App Insights custom metrics.

Bridges Continuous Evaluation into Continuous Monitoring by making
evaluation scores visible as time-series metrics in Application Insights.
"""

from __future__ import annotations

import logging

from opentelemetry import metrics

from src.config import get_settings

logger = logging.getLogger(__name__)

# Meter for CE score tracking
_meter = metrics.get_meter("ce-score-tracker")


def _create_counter(name: str, description: str) -> metrics.UpDownCounter:
    """Create an UpDownCounter for a score metric."""
    return _meter.create_up_down_counter(name=name, description=description, unit="score")


def track_scores(scores: dict[str, float], run_id: str = "") -> None:
    """Push evaluation scores as OpenTelemetry metrics to Application Insights.

    Each score is emitted as a custom metric with the evaluator name.
    These metrics appear in App Insights → Custom Metrics and can be
    visualized in the CE/CM dashboard.

    Args:
        scores: Dict mapping evaluator name to score (1-5 scale).
        run_id: Optional evaluation run identifier for correlation.
    """
    settings = get_settings()

    for evaluator, score in scores.items():
        metric_name = f"ce.eval.{evaluator}"
        counter = _create_counter(metric_name, f"CE evaluation score for {evaluator}")

        attributes = {
            "evaluator": evaluator,
            "run_id": run_id,
            "project": settings.ai_foundry.project,
        }

        # Record the score value
        counter.add(int(score * 100), attributes=attributes)  # Scale to integer for precision
        logger.info("Tracked metric %s = %.2f (run: %s)", metric_name, score, run_id)

    logger.info("All %d scores tracked as custom metrics", len(scores))
