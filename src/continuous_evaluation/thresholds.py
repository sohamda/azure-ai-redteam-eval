"""Central pass/warn/fail threshold definitions per evaluator.

These thresholds gate the CI/CD pipeline — scores below these levels block deployment.
Configurable via environment variables (CE_THRESHOLD_*).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from src.config import get_settings


class ThresholdStatus(StrEnum):
    """Evaluation threshold outcome."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class ThresholdResult:
    """Result of a threshold check for a single evaluator."""

    evaluator: str
    score: float
    threshold: float
    status: ThresholdStatus

    @property
    def passed(self) -> bool:
        """Whether the score meets the threshold."""
        return self.status == ThresholdStatus.PASS


def get_thresholds() -> dict[str, float]:
    """Load threshold definitions from settings.

    Returns:
        Dict mapping evaluator name to minimum acceptable score.
    """
    settings = get_settings()
    return {
        "groundedness": settings.thresholds.groundedness,
        "coherence": settings.thresholds.coherence,
        "relevance": settings.thresholds.relevance,
        "fluency": settings.thresholds.fluency,
        "safety": settings.thresholds.safety,
    }


def check_threshold(
    evaluator: str, score: float, threshold: float | None = None, warn_margin: float = 0.5
) -> ThresholdResult:
    """Check a single evaluator score against its threshold.

    Args:
        evaluator: Name of the evaluator (e.g. 'groundedness').
        score: The actual score from the evaluation run.
        threshold: Explicit threshold. If None, loaded from settings.
        warn_margin: Scores within this margin *below* threshold get WARN instead of FAIL.

    Returns:
        ThresholdResult with pass/warn/fail status.
    """
    if threshold is None:
        thresholds = get_thresholds()
        threshold = thresholds.get(evaluator, 4.0)

    if score >= threshold:
        status = ThresholdStatus.PASS
    elif score >= threshold - warn_margin:
        status = ThresholdStatus.WARN
    else:
        status = ThresholdStatus.FAIL

    return ThresholdResult(evaluator=evaluator, score=score, threshold=threshold, status=status)


def check_all_thresholds(scores: dict[str, float]) -> list[ThresholdResult]:
    """Check all evaluator scores against their thresholds.

    Only evaluators with defined thresholds are checked. Unknown evaluators
    (e.g. SDK-internal metrics like 'binary_aggregate') are skipped.

    Args:
        scores: Dict mapping evaluator name to score.

    Returns:
        List of ThresholdResults. Pipeline should fail if any result has FAIL status.
    """
    known_thresholds = get_thresholds()
    results: list[ThresholdResult] = []
    for evaluator, score in scores.items():
        # Normalize: strip 'gpt_' prefix to match base evaluator names
        base_name = evaluator.removeprefix("gpt_")
        if base_name in known_thresholds:
            results.append(check_threshold(evaluator, score, threshold=known_thresholds[base_name]))
    return results


def any_failures(results: list[ThresholdResult]) -> bool:
    """Check if any threshold results indicate a failure.

    Args:
        results: List of ThresholdResult from check_all_thresholds.

    Returns:
        True if at least one evaluator failed its threshold.
    """
    return any(r.status == ThresholdStatus.FAIL for r in results)
