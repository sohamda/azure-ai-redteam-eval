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
_telemetry_initialized: bool = False


def setup_telemetry() -> None:
    """Initialize OpenTelemetry with Azure Monitor exporter.

    Configures trace and metric exporters to send telemetry to
    Application Insights via the connection string. Sets up
    auto-instrumentation for FastAPI (requests table) and
    logging (traces table).
    """
    global _tracer, _meter, _telemetry_initialized  # noqa: PLW0603

    if _telemetry_initialized:
        logger.debug("Telemetry already initialized — skipping")
        return

    settings = get_settings()
    connection_string = settings.monitoring.applicationinsights_connection_string

    if connection_string:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(
                connection_string=connection_string,
                # Enable auto-instrumentation for FastAPI/ASGI so requests appear
                # in the 'requests' table and dependencies in 'dependencies' table.
                enable_live_metrics=True,
                logger_name="src",
            )
            logger.info("Azure Monitor telemetry configured (connection string present)")
        except ImportError:
            logger.warning("azure-monitor-opentelemetry not installed — using default SDK providers")
            trace.set_tracer_provider(TracerProvider())
            metrics.set_meter_provider(MeterProvider())
        except Exception as exc:
            logger.warning("Azure Monitor configuration failed (%s) — using default SDK providers", exc)
            trace.set_tracer_provider(TracerProvider())
            metrics.set_meter_provider(MeterProvider())
    else:
        logger.warning("No APPLICATIONINSIGHTS_CONNECTION_STRING — telemetry goes to SDK defaults (no export)")
        trace.set_tracer_provider(TracerProvider())
        metrics.set_meter_provider(MeterProvider())

    _tracer = trace.get_tracer("azure-ai-redteam-eval")
    _meter = metrics.get_meter("azure-ai-redteam-eval")
    _telemetry_initialized = True

    logger.info("Telemetry initialized (tracer + meter ready)")


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


def is_telemetry_configured() -> bool:
    """Check whether telemetry has been initialised with Azure Monitor.

    Returns:
        True if ``setup_telemetry`` ran and a connection string was present.
    """
    return _telemetry_initialized


def flush_telemetry(timeout_millis: int = 10_000) -> bool:
    """Force-flush all pending traces and metrics to the exporter.

    Call this before process exit (CLI scripts) or at the end of a
    CI evaluation run to make sure every data-point reaches App Insights.

    Args:
        timeout_millis: Maximum time (ms) to wait for the flush.

    Returns:
        True if flush succeeded, False otherwise.
    """
    ok = True

    # Flush traces
    tp = trace.get_tracer_provider()
    if hasattr(tp, "force_flush"):
        try:
            tp.force_flush(timeout_millis)  # type: ignore[arg-type]
            logger.info("Trace provider flushed")
        except Exception as exc:
            logger.warning("Trace flush failed: %s", exc)
            ok = False

    # Flush metrics
    mp = metrics.get_meter_provider()
    if hasattr(mp, "force_flush"):
        try:
            mp.force_flush(timeout_millis)  # type: ignore[arg-type]
            logger.info("Meter provider flushed")
        except Exception as exc:
            logger.warning("Metric flush failed: %s", exc)
            ok = False

    return ok
