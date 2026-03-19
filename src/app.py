"""FastAPI entrypoint for the multi-agent system.

Exposes a /chat endpoint that invokes the orchestrator agent.
This is the "application under evaluation" — kept lean and observable.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from opentelemetry import trace as _otrace
from pydantic import BaseModel

from src.agents.orchestrator import run_orchestrator
from src.config import get_settings
from src.continuous_monitoring.telemetry import create_agent_metrics, flush_telemetry, get_tracer, setup_telemetry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Incoming chat request."""

    query: str
    context: str = ""


class ChatResponse(BaseModel):
    """Chat response from the multi-agent system."""

    response: str
    agents_involved: list[str]


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown logic."""
    settings = get_settings()

    # Ensure application logs always reach stdout (App Service Log stream).
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
        root_logger.addHandler(handler)

    # Initialize OpenTelemetry → App Insights.
    # Must run inside lifespan (after uvicorn forks workers) so that the
    # TracerProvider's BatchSpanProcessor threads are owned by this process.
    setup_telemetry()

    # Create agent-level metrics (counters, histograms)
    app.state.agent_metrics = create_agent_metrics()

    logger.info("Starting azure-ai-redteam-eval agent service")
    logger.info("OpenAI endpoint: %s", settings.openai.endpoint)
    logger.info("AI Foundry project: %s", settings.ai_foundry.project)
    logger.info("Telemetry: App Insights connected=%s", bool(settings.monitoring.applicationinsights_connection_string))
    yield
    # Flush pending telemetry before shutdown so nothing is lost
    flush_telemetry(timeout_millis=10_000)
    logger.info("Shutting down agent service")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="CE/CM Demo — Multi-Agent Service",
    description="Application under Continuous Evaluation & Monitoring",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request telemetry middleware — creates explicit SERVER spans so inbound
# HTTP requests appear in App Insights 'requests' table.
# Uses a raw ASGI middleware (not BaseHTTPMiddleware) to avoid context
# propagation issues with Starlette's task-based dispatch.
# ---------------------------------------------------------------------------


class _RequestSpanMiddleware:
    """Raw ASGI middleware that wraps each HTTP request in a SERVER span."""

    def __init__(self, app):  # type: ignore[no-untyped-def]
        self.app = app

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        scheme = scope.get("scheme", "http")
        headers = dict(scope.get("headers", []))
        host = headers.get(b"host", b"").decode("utf-8", errors="replace")
        url = f"{scheme}://{host}{path}"

        tracer = _otrace.get_tracer("src.app")
        status_code = 200

        async def _send_wrapper(message):  # type: ignore[no-untyped-def]
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 200)
            await send(message)

        with tracer.start_as_current_span(
            f"{method} {path}",
            kind=_otrace.SpanKind.SERVER,
        ) as span:
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", url)
            span.set_attribute("http.target", path)
            span.set_attribute("http.scheme", scheme)
            span.set_attribute("http.host", host)
            span.set_attribute("http.request.method", method)
            span.set_attribute("url.full", url)
            span.set_attribute("url.path", path)
            span.set_attribute("url.scheme", scheme)
            span.set_attribute("server.address", host)
            await self.app(scope, receive, _send_wrapper)
            span.set_attribute("http.status_code", status_code)
            span.set_attribute("http.response.status_code", status_code)


app.add_middleware(_RequestSpanMiddleware)  # type: ignore[arg-type]


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the chat UI."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>CE/CM Demo — Multi-Agent Service</h1><p>POST /chat to interact.</p>")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a query through the multi-agent orchestrator.

    This endpoint is the primary target for:
    - Live demo during the talk
    - Continuous Evaluation (golden dataset queries)
    - Red-team probes (adversarial prompts)
    """
    tracer = get_tracer()
    start_time = time.perf_counter()

    with tracer.start_as_current_span("chat_request") as span:
        span.set_attribute("query.length", len(request.query))
        span.set_attribute("query.preview", request.query[:80])
        logger.info("Received chat request: %s", request.query[:80])

        # Get metrics instruments
        agent_metrics = getattr(app.state, "agent_metrics", None)

        try:
            result = await run_orchestrator(query=request.query, context=request.context)
            duration_ms = (time.perf_counter() - start_time) * 1000

            span.set_attribute("response.length", len(result.response))
            span.set_attribute("agents.involved", ",".join(result.agents_involved))
            span.set_attribute("duration_ms", duration_ms)
            span.set_attribute("status", "success")

            # Record metrics for CM dashboard
            if agent_metrics:
                for agent_name in result.agents_involved:
                    agent_metrics["request_count"].add(1, {"agent.name": agent_name})
                    agent_metrics["request_duration"].record(duration_ms, {"agent.name": agent_name})

            logger.info(
                "Response generated in %.0fms by agents: %s",
                duration_ms,
                result.agents_involved,
            )
            return ChatResponse(response=result.response, agents_involved=result.agents_involved)
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            span.set_attribute("status", "error")
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e)[:200])
            span.set_attribute("duration_ms", duration_ms)

            # Record error metric
            if agent_metrics:
                agent_metrics["error_count"].add(1, {"agent.name": "orchestrator", "error.type": type(e).__name__})

            logger.exception("Chat request failed after %.0fms", duration_ms)
            raise


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick demo mode: start the server and print a sample request
    print("=" * 60)
    print("  CE/CM Demo — Multi-Agent Service")
    print("  Continuous Evaluation & Monitoring for AI Applications")
    print("=" * 60)
    print()
    print("Starting server at http://localhost:8000")
    print("  POST /chat  — send queries to the agent orchestrator")
    print("  GET  /health — health check")
    print()

    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload="--reload" in sys.argv,
    )
