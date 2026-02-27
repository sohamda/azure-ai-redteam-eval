"""Validate Telemetry — sends test metrics/traces to App Insights.

Run this after deploying or configuring APPLICATIONINSIGHTS_CONNECTION_STRING
to verify data shows up in the Workbook. Typical latency: 2-5 minutes.

Usage:
    python -m scripts.validate_telemetry          # send test data
    python -m scripts.validate_telemetry --query   # also run KQL query to check
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_settings
from src.continuous_monitoring.telemetry import flush_telemetry, get_meter, get_tracer, setup_telemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Test data that exercises every workbook panel
# ---------------------------------------------------------------------------

SAMPLE_EVAL_SCORES: dict[str, float] = {
    "groundedness": 4.2,
    "coherence": 4.5,
    "relevance": 4.1,
    "fluency": 4.8,
    "safety": 5.0,
}

SAMPLE_REDTEAM_RESULTS: dict[str, dict[str, int]] = {
    "prompt_injection": {"passed": 8, "failed": 2},
    "jailbreak": {"passed": 9, "failed": 1},
    "pii_extraction": {"passed": 10, "failed": 0},
}


def emit_test_traces() -> None:
    """Emit test traces that should appear in the 'traces' table."""
    tracer = get_tracer()

    with tracer.start_as_current_span("validate_telemetry.test_root") as root:
        root.set_attribute("test", True)
        logger.info("Validation: emitting test root span")

        with tracer.start_as_current_span("agent.planner-agent") as span:
            span.set_attribute("agent.name", "planner-agent")
            span.set_attribute("agent.status", "success")
            time.sleep(0.05)

        with tracer.start_as_current_span("agent.retrieval-agent") as span:
            span.set_attribute("agent.name", "retrieval-agent")
            span.set_attribute("agent.status", "success")
            time.sleep(0.03)

        with tracer.start_as_current_span("agent.safety-agent") as span:
            span.set_attribute("agent.name", "safety-agent")
            span.set_attribute("agent.status", "success")
            time.sleep(0.02)

    logger.info("Validation: 4 test spans emitted")


def emit_test_agent_metrics() -> None:
    """Emit test agent metrics (agent.request.*, agent.error.*)."""
    from src.continuous_monitoring.telemetry import create_agent_metrics

    agent_metrics = create_agent_metrics()

    for agent_name in ["planner-agent", "retrieval-agent", "safety-agent"]:
        agent_metrics["request_count"].add(1, {"agent.name": agent_name})
        agent_metrics["request_duration"].record(250.0 + hash(agent_name) % 500, {"agent.name": agent_name})

    agent_metrics["error_count"].add(1, {"agent.name": "safety-agent", "error.type": "ContentFilterError"})
    logger.info("Validation: agent metrics emitted (request count, duration, error)")


def emit_test_eval_scores() -> None:
    """Emit CE evaluation scores using the real exporter."""
    from src.continuous_monitoring.eval_metrics_exporter import export_eval_scores

    export_eval_scores(
        scores=SAMPLE_EVAL_SCORES,
        evaluation_name="validation-test",
        run_id="validate-001",
    )
    logger.info("Validation: evaluation scores emitted via eval_metrics_exporter")


def emit_test_score_tracker() -> None:
    """Emit CE evaluation scores using the score_tracker (same prefix)."""
    from src.continuous_evaluation.score_tracker import track_scores

    track_scores(scores=SAMPLE_EVAL_SCORES, run_id="validate-tracker-001")
    logger.info("Validation: evaluation scores emitted via score_tracker")


def emit_test_redteam_metrics() -> None:
    """Emit red-team metrics."""
    from src.continuous_monitoring.eval_metrics_exporter import export_redteam_metrics

    export_redteam_metrics(
        category_results=SAMPLE_REDTEAM_RESULTS,
        run_id="validate-rt-001",
    )
    logger.info("Validation: red-team metrics emitted")


def run_validation(do_query: bool = False) -> None:
    """Run the full validation pipeline."""
    settings = get_settings()
    conn_str = settings.monitoring.applicationinsights_connection_string

    print("=" * 60)
    print("  Telemetry Validation — CE/CM Dashboard")
    print("=" * 60)
    print()

    if not conn_str:
        print("ERROR: APPLICATIONINSIGHTS_CONNECTION_STRING is not set.")
        print("       Set it in .env or as an environment variable.")
        print("       Without it, metrics go to the no-op OTel provider.")
        sys.exit(1)

    print(f"  Connection string: {conn_str[:40]}...")
    print()

    # 1. Initialize telemetry (configures Azure Monitor)
    print("[1/6] Initializing telemetry...")
    setup_telemetry()

    # 2. Emit traces
    print("[2/6] Emitting test traces (spans)...")
    emit_test_traces()

    # 3. Emit agent metrics
    print("[3/6] Emitting agent metrics (request count, duration, errors)...")
    emit_test_agent_metrics()

    # 4. Emit eval scores
    print("[4/6] Emitting CE evaluation scores...")
    emit_test_eval_scores()

    # 5. Emit score tracker scores
    print("[5/6] Emitting score tracker scores...")
    emit_test_score_tracker()

    # 6. Emit red-team metrics
    print("[6/6] Emitting red-team metrics...")
    emit_test_redteam_metrics()

    # Flush everything
    print()
    print("Flushing all telemetry to Azure Monitor...")
    success = flush_telemetry(timeout_millis=30_000)

    print()
    if success:
        print("SUCCESS: All telemetry flushed.")
    else:
        print("WARNING: Flush may not have completed — check App Insights in 2-5 minutes.")

    print()
    print("Next steps:")
    print("  1. Wait 2-5 minutes for data ingestion.")
    print("  2. Open Application Insights > Logs (Log Analytics).")
    print("  3. Run this KQL to verify data arrived:")
    print()
    print("     customMetrics")
    print("     | where name startswith 'ce.' or name startswith 'agent.'")
    print("     | summarize count() by name")
    print("     | order by name asc")
    print()
    print("  4. Open the CE/CM Dashboard Workbook — section 0 (Health Check)")
    print("     should now show data in 'Custom Metrics Inventory'.")

    if do_query:
        print()
        print("(--query flag detected, but KQL query requires Azure SDK auth — check manually)")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate CE/CM telemetry pipeline")
    parser.add_argument("--query", action="store_true", help="Also attempt to query App Insights (requires auth)")
    args = parser.parse_args()
    run_validation(do_query=args.query)


if __name__ == "__main__":
    main()
