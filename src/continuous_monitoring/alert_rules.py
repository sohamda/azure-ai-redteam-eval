"""Alert Rules — defines alert conditions for CE/CM.

Programmatic definitions that correspond to infra/modules/alerts.bicep.
Used for validation and documentation of alert thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AlertSeverity(int, Enum):
    """Azure Monitor alert severity levels."""

    CRITICAL = 0
    ERROR = 1
    WARNING = 2
    INFORMATIONAL = 3
    VERBOSE = 4


@dataclass
class AlertRule:
    """Definition of an alert rule for CE/CM monitoring."""

    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    condition: str
    threshold: float
    evaluation_frequency: str = "PT5M"
    window_size: str = "PT15M"
    auto_mitigate: bool = True


# ---------------------------------------------------------------------------
# Alert rule definitions — these match infra/modules/alerts.bicep
# ---------------------------------------------------------------------------


def get_alert_rules() -> list[AlertRule]:
    """Get all CE/CM alert rule definitions.

    Returns:
        List of AlertRule definitions for deployment via Bicep.
    """
    return [
        # CE: Evaluation score alerts
        AlertRule(
            name="ce-groundedness-drop",
            description="Groundedness score dropped below threshold",
            severity=AlertSeverity.ERROR,
            metric_name="ce.score.groundedness",
            condition="LessThan",
            threshold=4.0,
        ),
        AlertRule(
            name="ce-coherence-drop",
            description="Coherence score dropped below threshold",
            severity=AlertSeverity.WARNING,
            metric_name="ce.score.coherence",
            condition="LessThan",
            threshold=4.0,
        ),
        AlertRule(
            name="ce-relevance-drop",
            description="Relevance score dropped below threshold",
            severity=AlertSeverity.WARNING,
            metric_name="ce.score.relevance",
            condition="LessThan",
            threshold=4.0,
        ),
        AlertRule(
            name="ce-safety-violation",
            description="Safety score dropped below critical threshold",
            severity=AlertSeverity.CRITICAL,
            metric_name="ce.score.safety",
            condition="LessThan",
            threshold=5.0,
            evaluation_frequency="PT1M",
            window_size="PT5M",
        ),
        # CM: Agent health alerts
        AlertRule(
            name="cm-agent-latency-p99",
            description="Agent P99 latency exceeded threshold",
            severity=AlertSeverity.WARNING,
            metric_name="agent.request.duration",
            condition="GreaterThan",
            threshold=5000.0,  # 5 seconds
        ),
        AlertRule(
            name="cm-agent-error-rate",
            description="Agent error rate exceeded threshold",
            severity=AlertSeverity.ERROR,
            metric_name="agent.error.count",
            condition="GreaterThan",
            threshold=10.0,
            window_size="PT5M",
        ),
        # CE: Red-team alerts
        AlertRule(
            name="ce-redteam-failures",
            description="Red team probes detected safety bypass",
            severity=AlertSeverity.CRITICAL,
            metric_name="ce.redteam.failed",
            condition="GreaterThan",
            threshold=0.0,
            evaluation_frequency="PT1M",
            window_size="PT5M",
        ),
    ]
