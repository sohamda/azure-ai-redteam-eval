"""Red Team entry point — invokes adversarial probes against the agent system.

Uses the azure-ai-evaluation RedTeam SDK for automated adversarial scanning,
with a custom-probes fallback via attack_strategies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
from azure.identity import DefaultAzureCredential

from src.config import configure_logging, get_settings
from src.redteam.attack_strategies import (
    TargetUnreachableError,
    get_attack_categories,
    run_adversarial_probes,
)
from src.redteam.report import generate_report

logger = logging.getLogger(__name__)

ADVERSARIAL_DATASET = Path(__file__).parent.parent / "continuous_evaluation" / "datasets" / "adversarial_prompts.jsonl"
REPORT_OUTPUT = Path("redteam_report.json")
REPORT_MD_OUTPUT = Path("redteam_report.md")
# Dedicated dir for the SDK scan artifacts so they don't clobber the CE
# outputs (evaluation_results.json / results.json) written at the repo root.
SDK_SCAN_OUTPUT_DIR = Path("redteam_scan_output")

# Risk categories to test
RISK_CATEGORIES: list[RiskCategory] = [
    RiskCategory.Violence,
    RiskCategory.HateUnfairness,
    RiskCategory.Sexual,
    RiskCategory.SelfHarm,
]

# Attack strategies — single-turn only (Crescendo/MultiTurn must be run alone)
ATTACK_STRATEGIES: list[AttackStrategy | list[AttackStrategy]] = [
    AttackStrategy.Baseline,
    AttackStrategy.Jailbreak,
]


def _build_target_callback(endpoint: str) -> Any:
    """Build the target callback used by the RedTeam SDK.

    The azure-ai-evaluation ``_CallbackChatTarget`` invokes this with keyword
    args ``messages`` (chat history), ``stream``, ``session_state`` and
    ``context``, and expects a dict shaped like
    ``{"messages": [{"role": "assistant", "content": <text>}]}`` in return.

    Args:
        endpoint: The chat API endpoint URL.

    Returns:
        An async callback compatible with the RedTeam SDK.
    """
    import httpx

    async def target_callback(
        messages: list[dict[str, Any]],
        stream: bool = False,
        session_state: Any = None,
        context: Any = None,
    ) -> dict[str, Any]:
        """Forward the latest user turn to the agent and wrap the reply."""
        query = messages[-1]["content"] if messages else ""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(endpoint, json={"query": query, "context": ""})
                resp.raise_for_status()
                answer = str(resp.json().get("response", ""))
            except Exception as e:
                logger.warning("Target callback error: %s", e)
                answer = f"Error: {e}"
        return {"messages": [{"role": "assistant", "content": answer}]}

    return target_callback


async def run_redteam_sdk(endpoint: str = "http://localhost:8000/chat") -> dict[str, Any]:
    """Run red-team scan using the Azure AI Evaluation RedTeam SDK.

    This uses Microsoft's service-side attack objective generation and
    automated adversarial probes (jailbreak, crescendo, etc.).

    Args:
        endpoint: The chat API endpoint URL.

    Returns:
        Scan result dict.
    """
    settings = get_settings()
    credential = DefaultAzureCredential()

    azure_ai_project = {
        "subscription_id": settings.azure.subscription_id,
        "resource_group_name": settings.azure.resource_group,
        "project_name": settings.ai_foundry.project,
    }

    logger.info("Initializing RedTeam SDK with project: %s", azure_ai_project)

    red_team = RedTeam(
        azure_ai_project=azure_ai_project,
        credential=credential,
        risk_categories=RISK_CATEGORIES,
        num_objectives=5,
        application_scenario=(
            "A multi-agent AI assistant that helps users with general-purpose questions. "
            "It uses a planner, retrieval, and safety agent to generate responses."
        ),
    )

    target = _build_target_callback(endpoint)

    strategy_names = [
        s.name if hasattr(s, "name") else str(s)  # type: ignore[union-attr]
        for s in ATTACK_STRATEGIES
    ]
    logger.info("Running red-team scan with strategies: %s", strategy_names)

    SDK_SCAN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = await red_team.scan(
        target=target,
        scan_name="ce-redteam-scan",
        attack_strategies=ATTACK_STRATEGIES,
        output_path=str(SDK_SCAN_OUTPUT_DIR),
        skip_upload=True,
    )

    return result  # type: ignore[return-value]


async def run_redteam_custom(endpoint: str = "http://localhost:8000/chat") -> dict[str, list[dict[str, str]]]:
    """Run red-team using custom adversarial probes from the local dataset.

    This is the fallback / complement to the SDK-based scan — fires known
    attack prompts and checks if the agent blocks them.

    Args:
        endpoint: The chat API endpoint URL.

    Returns:
        Dict mapping attack category to list of probe results.
    """
    settings = get_settings()

    if not ADVERSARIAL_DATASET.exists():
        logger.error("Adversarial dataset not found: %s", ADVERSARIAL_DATASET)
        sys.exit(1)

    prompts: list[dict[str, str]] = []
    with ADVERSARIAL_DATASET.open() as f:
        for line in f:
            prompts.append(json.loads(line.strip()))

    logger.info("Loaded %d custom adversarial prompts", len(prompts))

    categories = get_attack_categories()
    logger.info("Attack categories: %s", list(categories.keys()))

    results = await run_adversarial_probes(
        prompts=prompts,
        endpoint=endpoint,
        settings=settings,
    )

    return results


def _resolve_target_url() -> str:
    """Resolve the target URL from CLI args or environment.

    Priority: --target-url CLI flag > REDTEAM_TARGET_URL env var > default localhost.

    Returns:
        The resolved chat endpoint URL.
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run AI Red Team probes", add_help=False)
    parser.add_argument("--target-url", type=str, default=None, help="Target chat endpoint URL")
    args, _ = parser.parse_known_args()

    if args.target_url:
        return args.target_url

    env_url = os.environ.get("REDTEAM_TARGET_URL")
    if env_url:
        return env_url

    return "http://localhost:8000/chat"


async def _check_target_health(chat_endpoint: str) -> None:
    """Verify the agent service is reachable before probing.

    Args:
        chat_endpoint: The chat API endpoint URL (e.g. .../chat).

    Raises:
        TargetUnreachableError: If the health endpoint cannot be reached.
    """
    from urllib.parse import urlsplit, urlunsplit

    import httpx

    parts = urlsplit(chat_endpoint)
    health_url = urlunsplit((parts.scheme, parts.netloc, "/health", "", ""))
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(health_url)
            resp.raise_for_status()
        except Exception as e:
            raise TargetUnreachableError(
                f"Agents are not running — target endpoint {chat_endpoint} is unreachable "
                f"({health_url} failed: {e}). Start the service with `python -m src.app` and retry."
            ) from e


async def run_redteam() -> None:
    """Run the full red-team evaluation — SDK scan + custom probes.

    Generates a combined report with pass/fail per category.
    Target URL is resolved from --target-url CLI flag, REDTEAM_TARGET_URL
    env var, or defaults to http://localhost:8000/chat.

    Raises:
        SystemExit: If critical findings are detected.
    """
    configure_logging()

    logger.info("=" * 60)
    logger.info("AI RED TEAMING — Adversarial Evaluation")
    logger.info("=" * 60)

    endpoint = _resolve_target_url()
    logger.info("Target endpoint: %s", endpoint)
    has_critical = False

    # Preflight: abort immediately if the agent service is not running.
    try:
        await _check_target_health(endpoint)
    except TargetUnreachableError as e:
        logger.error("%s", e)
        sys.exit(2)

    # --- Phase 1: Azure AI Evaluation RedTeam SDK scan ---
    logger.info("--- Phase 1: RedTeam SDK Scan ---")
    try:
        sdk_result = await run_redteam_sdk(endpoint=endpoint)
        logger.info("RedTeam SDK scan completed.")
        # Save the structured scan result (RedTeamResult.to_json emits scan_result).
        sdk_output = Path("redteam_sdk_result.json")
        to_json = getattr(sdk_result, "to_json", None)
        sdk_json = str(to_json()) if callable(to_json) else ""
        payload = sdk_json if sdk_json else json.dumps({"scan_result": None}, indent=2)
        sdk_output.write_text(payload, encoding="utf-8")
        logger.info("SDK scan result saved to %s", sdk_output)
    except Exception as e:
        logger.warning("RedTeam SDK scan failed (non-blocking): %s", e)
        logger.info("Continuing with custom probes...")

    # --- Phase 2: Custom adversarial probes ---
    logger.info("--- Phase 2: Custom Adversarial Probes ---")
    try:
        custom_results = await run_redteam_custom(endpoint=endpoint)
    except TargetUnreachableError as e:
        logger.error("%s", e)
        sys.exit(2)

    # Generate reports from custom probes
    report_json, report_md, has_critical = generate_report(custom_results)

    with REPORT_OUTPUT.open("w") as f:
        json.dump(report_json, f, indent=2)
    REPORT_MD_OUTPUT.write_text(report_md, encoding="utf-8")

    logger.info("Reports saved: %s, %s", REPORT_OUTPUT, REPORT_MD_OUTPUT)
    print(report_md)

    if has_critical:
        logger.error("CRITICAL FINDINGS DETECTED — deployment is unsafe.")
        sys.exit(1)

    logger.info("Red teaming completed — no critical findings.")


def main() -> None:
    """CLI entry point for `python -m src.redteam.run_redteam`."""
    asyncio.run(run_redteam())


if __name__ == "__main__":
    main()
