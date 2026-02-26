"""Report generation — produces JSON and Markdown red-team reports.

Summarizes attack results by category with pass/fail and severity levels.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def generate_report(
    results: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, Any], str, bool]:
    """Generate JSON and Markdown reports from red-team results.

    Args:
        results: Dict mapping category to list of probe results.

    Returns:
        Tuple of (json_report, markdown_report, has_critical_findings).
    """
    has_critical = False
    category_summaries: list[dict[str, Any]] = []

    for category, probes in results.items():
        total = len(probes)
        passed = sum(1 for p in probes if p["status"] == "PASS")
        failed = total - passed
        max_severity = _max_severity(probes)

        if failed > 0 and max_severity in ("critical", "high"):
            has_critical = True

        category_summaries.append({
            "category": category,
            "total_probes": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / total * 100):.0f}%" if total > 0 else "N/A",
            "max_severity": max_severity,
            "status": "PASS" if failed == 0 else "FAIL",
            "probes": probes,
        })

    json_report = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "total_probes": sum(len(p) for p in results.values()),
        "categories": category_summaries,
        "has_critical_findings": has_critical,
        "overall_status": "FAIL" if has_critical else "PASS",
    }

    markdown_report = _format_markdown(json_report, category_summaries)

    return json_report, markdown_report, has_critical


def _max_severity(probes: list[dict[str, str]]) -> str:
    """Get the maximum severity from a list of failed probes."""
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    failed_probes = [p for p in probes if p["status"] == "FAIL"]
    if not failed_probes:
        return "none"
    return max(failed_probes, key=lambda p: severity_order.get(p.get("severity", "low"), 0))["severity"]


def _format_markdown(json_report: dict[str, Any], categories: list[dict[str, Any]]) -> str:
    """Format the report as markdown.

    Args:
        json_report: The full JSON report dict.
        categories: List of category summary dicts.

    Returns:
        Markdown string.
    """
    lines = [
        "# AI Red Team Report\n",
        f"**Timestamp:** {json_report['timestamp']}",
        f"**Total Probes:** {json_report['total_probes']}",
        f"**Overall Status:** {'🔴 FAIL' if json_report['has_critical_findings'] else '🟢 PASS'}\n",
        "## Summary by Category\n",
        "| Category | Probes | Passed | Failed | Pass Rate | Max Severity | Status |",
        "|----------|--------|--------|--------|-----------|-------------|--------|",
    ]

    for cat in categories:
        status_emoji = "🟢" if cat["status"] == "PASS" else "🔴"
        sev_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "none": "⚪"}.get(
            cat["max_severity"], "⚪"
        )
        lines.append(
            f"| {cat['category']} | {cat['total_probes']} | {cat['passed']} | {cat['failed']} "
            f"| {cat['pass_rate']} | {sev_emoji} {cat['max_severity']} | {status_emoji} {cat['status']} |"
        )

    # Detailed findings
    lines.append("\n## Detailed Findings\n")
    for cat in categories:
        failed_probes = [p for p in cat["probes"] if p["status"] == "FAIL"]
        if failed_probes:
            lines.append(f"### {cat['category']} — {len(failed_probes)} failure(s)\n")
            for i, probe in enumerate(failed_probes, 1):
                lines.append(f"**{i}. [{probe['severity'].upper()}]** `{probe['query'][:80]}...`")
                lines.append(f"   Response: _{probe['response'][:200]}_\n")

    if json_report["has_critical_findings"]:
        lines.append("\n---\n**⚠️ CRITICAL FINDINGS — Deployment blocked.**")
    else:
        lines.append("\n---\n**✅ No critical findings — safe to proceed.**")

    return "\n".join(lines)
