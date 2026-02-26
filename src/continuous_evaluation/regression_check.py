"""Regression Check — compares current eval scores against a stored baseline.

Detects quality regressions and blocks deployment when scores drop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

BASELINE_PATH = Path("evaluation_baseline.json")
CURRENT_PATH = Path("evaluation_results.json")
COMPARISON_OUTPUT = Path("regression_comparison.md")


def load_scores(path: Path | str) -> dict[str, float]:
    """Load evaluation scores from a JSON file.

    Args:
        path: Path to the JSON file containing scores.

    Returns:
        Dict mapping evaluator name to score.
    """
    p = Path(path) if isinstance(path, str) else path
    if not p.exists():
        return {}
    with p.open() as f:
        data: dict[str, float] = json.load(f)
    return data.get("scores", data)  # type: ignore[return-value]


def compare_scores(
    baseline: dict[str, float],
    current: dict[str, float],
    regression_threshold: float = 0.3,
) -> tuple[list[dict[str, float | str]], bool]:
    """Compare current scores against baseline, detect regressions.

    Args:
        baseline: Previous evaluation scores.
        current: Current evaluation scores.
        regression_threshold: Score drop that constitutes a regression.

    Returns:
        Tuple of (comparison list, has_regression bool).
    """
    comparisons: list[dict[str, float | str]] = []
    has_regression = False

    all_evaluators = set(baseline.keys()) | set(current.keys())
    for evaluator in sorted(all_evaluators):
        base_score = baseline.get(evaluator, 0.0)
        curr_score = current.get(evaluator, 0.0)
        delta = curr_score - base_score

        if delta < -regression_threshold:
            status = "REGRESSION"
            has_regression = True
        elif delta < 0:
            status = "SLIGHT DROP"
        elif delta > regression_threshold:
            status = "IMPROVED"
        else:
            status = "STABLE"

        comparisons.append({
            "evaluator": evaluator,
            "baseline": base_score,
            "current": curr_score,
            "delta": round(delta, 3),
            "status": status,
        })

    return comparisons, has_regression


def format_comparison_markdown(comparisons: list[dict[str, float | str]], has_regression: bool) -> str:
    """Format comparison results as a markdown table.

    Args:
        comparisons: List of comparison dicts from compare_scores.
        has_regression: Whether any regression was detected.

    Returns:
        Markdown string with comparison table.
    """
    lines = [
        "# Regression Check Results\n",
        "| Evaluator | Baseline | Current | Delta | Status |",
        "|-----------|----------|---------|-------|--------|",
    ]

    for c in comparisons:
        delta_str = f"+{c['delta']}" if float(str(c["delta"])) > 0 else str(c["delta"])
        emoji = {"REGRESSION": "🔴", "SLIGHT DROP": "🟡", "IMPROVED": "🟢", "STABLE": "⚪"}.get(
            str(c["status"]), "⚪"
        )
        lines.append(
            f"| {c['evaluator']} | {c['baseline']:.2f} | {c['current']:.2f} | {delta_str} | {emoji} {c['status']} |"
        )

    if has_regression:
        lines.append("\n**REGRESSION DETECTED** — deployment blocked.")
    else:
        lines.append("\n**No regressions detected** — safe to proceed.")

    return "\n".join(lines)


async def run_regression_check() -> bool:
    """Run the regression check comparing current vs. baseline scores.

    Returns:
        True if no regressions detected, False if regressions found.

    Raises:
        SystemExit: If regressions are detected (blocks CI pipeline).
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    logger.info("=" * 60)
    logger.info("REGRESSION CHECK — Comparing current vs. baseline")
    logger.info("=" * 60)

    if not CURRENT_PATH.exists():
        logger.error("Current results not found: %s. Run evaluation first.", CURRENT_PATH)
        sys.exit(1)

    if not BASELINE_PATH.exists():
        logger.warning("No baseline found at %s. Setting current results as baseline.", BASELINE_PATH)
        import shutil

        shutil.copy(CURRENT_PATH, BASELINE_PATH)
        print("Baseline created from current results. No comparison possible on first run.")
        return True

    baseline = load_scores(BASELINE_PATH)
    current = load_scores(CURRENT_PATH)

    comparisons, has_regression = compare_scores(baseline, current)
    report = format_comparison_markdown(comparisons, has_regression)

    print(report)

    # Save comparison report
    COMPARISON_OUTPUT.write_text(report)
    logger.info("Comparison saved to %s", COMPARISON_OUTPUT)

    if has_regression:
        logger.error("REGRESSION DETECTED — deployment blocked.")
        sys.exit(1)

    logger.info("No regressions — safe to proceed.")
    return True


def main() -> None:
    """CLI entry point for `python -m src.continuous_evaluation.regression_check`."""
    asyncio.run(run_regression_check())


if __name__ == "__main__":
    main()
