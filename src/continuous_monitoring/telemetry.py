"""Telemetry — OpenTelemetry + Application Insights instrumentation.

Instruments every agent call, LLM invocation, and evaluation run
with structured traces and metrics exported to App Insights.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

from src.config import get_settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# Global tracer and meter
_tracer: trace.Tracer | None = None
_meter: metrics.Meter | None = None


def setup_telemetry() -> None:
    """Initialize OpenTelemetry with Azure Monitor exporter.

    Configures trace and metric exporters to send telemetry to
    Application Insights via the connection string.
    """
    global _tracer, _meter  # noqa: PLW0603

    settings = get_settings()
    connection_string = settings.monitoring.applicationinsights_connection_string

    if connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=connection_string)
            logger.info("Azure Monitor telemetry configured")
        except ImportError:
            logger.warning("azure-monitor-opentelemetry not installed — using default providers")
            trace.set_tracer_provider(TracerProvider())
            metrics.set_meter_provider(MeterProvider())
    else:
        logger.warning("No App Insights connection string — telemetry disabled")
        trace.set_tracer_provider(TracerProvider())
        metrics.set_meter_provider(MeterProvider())

    _tracer = trace.get_tracer("azure-ai-redteam-eval")
    _meter = metrics.get_meter("azure-ai-redteam-eval")

    logger.info("Telemetry initialized")


def get_tracer() -> trace.Tracer:
    """Get the application tracer, initializing if needed."""
    global _tracer  # noqa: PLW0603
    if _tracer is None:
        setup_telemetry()
    assert _tracer is not None
    return _tracer


def get_meter() -> metrics.Meter:
    """Get the application meter, initializing if needed."""
    global _meter  # noqa: PLW0603
    if _meter is None:
        setup_telemetry()
    assert _meter is not None
    return _meter


def trace_agent(agent_name: str) -> Callable[[F], F]:
    """Decorator to trace agent invocations.

    Creates a span for each agent call with the agent name,
    input length, and output length as attributes.

    Args:
        agent_name: Name of the agent being traced.

    Returns:
        Decorator function.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            with tracer.start_as_current_span(f"agent.{agent_name}") as span:
                span.set_attribute("agent.name", agent_name)
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("agent.status", "success")
                    return result
                except Exception as e:
                    span.set_attribute("agent.status", "error")
                    span.set_attribute("agent.error", str(e))
                    raise

        return wrapper  # type: ignore[return-value]

    return decorator


# Pre-defined metrics
def create_agent_metrics() -> dict[str, Any]:
    """Create standard agent-level metrics.

    Returns:
        Dict of metric instruments for agent health tracking.
    """
    meter = get_meter()
    return {
        "request_count": meter.create_counter(
            name="agent.request.count",
            description="Number of agent requests",
            unit="requests",
        ),
        "request_duration": meter.create_histogram(
            name="agent.request.duration",
            description="Agent request duration in milliseconds",
            unit="ms",
        ),
        "token_usage": meter.create_counter(
            name="agent.token.usage",
            description="Total tokens consumed by agent",
            unit="tokens",
        ),
        "error_count": meter.create_counter(
            name="agent.error.count",
            description="Number of agent errors",
            unit="errors",
        ),
    }
