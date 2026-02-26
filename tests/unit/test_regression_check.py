"""Tests for regression check logic."""

from __future__ import annotations

import json
from pathlib import Path

from src.continuous_evaluation.regression_check import (
    compare_scores,
    format_comparison_markdown,
    load_scores,
)


class TestLoadScores:
    """Tests for loading scores from JSON files."""

    def test_load_valid_json(self, tmp_path: Path) -> None:
        scores_file = tmp_path / "scores.json"
        scores_data = {"groundedness": 4.5, "coherence": 4.2}
        scores_file.write_text(json.dumps(scores_data))
        result = load_scores(scores_file)
        assert result == scores_data

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        result = load_scores(tmp_path / "nonexistent.json")
        assert result == {}


class TestCompareScores:
    """Tests for score comparison logic."""

    def test_no_regression(self) -> None:
        baseline = {"groundedness": 4.0, "coherence": 4.0}
        current = {"groundedness": 4.5, "coherence": 4.2}
        comparisons, has_regression = compare_scores(baseline, current)
        assert not has_regression
        assert all(c["status"] != "REGRESSION" for c in comparisons)

    def test_detects_regression(self) -> None:
        baseline = {"groundedness": 4.5}
        current = {"groundedness": 3.8}
        comparisons, has_regression = compare_scores(baseline, current, regression_threshold=0.3)
        assert has_regression
        assert any(c["status"] == "REGRESSION" for c in comparisons)

    def test_small_drop_no_regression(self) -> None:
        baseline = {"groundedness": 4.5}
        current = {"groundedness": 4.3}
        _comparisons, has_regression = compare_scores(baseline, current, regression_threshold=0.3)
        assert not has_regression

    def test_new_metric_in_current(self) -> None:
        baseline = {"groundedness": 4.0}
        current = {"groundedness": 4.5, "coherence": 4.2}
        comparisons, _has_regression = compare_scores(baseline, current)
        evaluators = [c["evaluator"] for c in comparisons]
        assert "coherence" in evaluators

    def test_empty_baseline(self) -> None:
        baseline: dict[str, float] = {}
        current = {"groundedness": 4.5}
        comparisons, has_regression = compare_scores(baseline, current)
        assert len(comparisons) == 1
        assert not has_regression


class TestFormatComparisonMarkdown:
    """Tests for markdown report formatting."""

    def test_produces_markdown_string(self) -> None:
        comparisons: list[dict[str, float | str]] = [
            {
                "evaluator": "groundedness",
                "baseline": 4.0,
                "current": 4.5,
                "delta": 0.5,
                "status": "IMPROVED",
            }
        ]
        md = format_comparison_markdown(comparisons, has_regression=False)
        assert isinstance(md, str)
        assert "groundedness" in md

    def test_regression_marked_in_output(self) -> None:
        comparisons: list[dict[str, float | str]] = [
            {
                "evaluator": "groundedness",
                "baseline": 4.5,
                "current": 3.5,
                "delta": -1.0,
                "status": "REGRESSION",
            }
        ]
        md = format_comparison_markdown(comparisons, has_regression=True)
        # Should contain a regression indicator
        assert "regression" in md.lower() or "❌" in md or "FAIL" in md or "🔴" in md
