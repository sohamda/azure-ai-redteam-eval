"""Tests for threshold checking logic."""

from __future__ import annotations

from src.continuous_evaluation.thresholds import (
    ThresholdResult,
    ThresholdStatus,
    any_failures,
    check_all_thresholds,
    check_threshold,
    get_thresholds,
)


class TestGetThresholds:
    """Tests for threshold retrieval."""

    def test_returns_dict(self) -> None:
        thresholds = get_thresholds()
        assert isinstance(thresholds, dict)

    def test_contains_expected_keys(self) -> None:
        thresholds = get_thresholds()
        expected_keys = {"groundedness", "coherence", "relevance", "fluency", "safety"}
        assert expected_keys.issubset(set(thresholds.keys()))

    def test_all_values_are_positive(self) -> None:
        thresholds = get_thresholds()
        for key, value in thresholds.items():
            assert value > 0, f"Threshold for {key} should be positive"


class TestCheckThreshold:
    """Tests for individual threshold checks."""

    def test_pass_when_above_threshold(self) -> None:
        result = check_threshold("groundedness", 4.5, 4.0)
        assert result.status == ThresholdStatus.PASS

    def test_fail_when_below_threshold(self) -> None:
        result = check_threshold("groundedness", 3.0, 4.0)
        assert result.status == ThresholdStatus.FAIL

    def test_warn_when_near_threshold(self) -> None:
        result = check_threshold("groundedness", 3.8, 4.0)
        assert result.status == ThresholdStatus.WARN

    def test_exact_threshold_is_pass(self) -> None:
        result = check_threshold("groundedness", 4.0, 4.0)
        assert result.status == ThresholdStatus.PASS

    def test_result_contains_evaluator_name(self) -> None:
        result = check_threshold("coherence", 4.5, 4.0)
        assert result.evaluator == "coherence"

    def test_result_contains_score(self) -> None:
        result = check_threshold("coherence", 4.5, 4.0)
        assert result.score == 4.5


class TestCheckAllThresholds:
    """Tests for batch threshold checking."""

    def test_all_passing_scores(self) -> None:
        scores = {"groundedness": 5.0, "coherence": 5.0, "relevance": 5.0, "fluency": 5.0, "safety": 5.0}
        results = check_all_thresholds(scores)
        assert all(r.status == ThresholdStatus.PASS for r in results)

    def test_mixed_scores(self) -> None:
        scores = {"groundedness": 5.0, "coherence": 2.0, "relevance": 5.0, "fluency": 5.0, "safety": 5.0}
        results = check_all_thresholds(scores)
        statuses = {r.evaluator: r.status for r in results}
        assert statuses["groundedness"] == ThresholdStatus.PASS
        assert statuses["coherence"] == ThresholdStatus.FAIL

    def test_returns_list_of_threshold_results(self) -> None:
        scores = {"groundedness": 4.5}
        results = check_all_thresholds(scores)
        assert all(isinstance(r, ThresholdResult) for r in results)


class TestAnyFailures:
    """Tests for failure detection."""

    def test_no_failures(self) -> None:
        results = [
            ThresholdResult(evaluator="a", score=5.0, threshold=4.0, status=ThresholdStatus.PASS),
            ThresholdResult(evaluator="b", score=3.8, threshold=4.0, status=ThresholdStatus.WARN),
        ]
        assert not any_failures(results)

    def test_has_failures(self) -> None:
        results = [
            ThresholdResult(evaluator="a", score=5.0, threshold=4.0, status=ThresholdStatus.PASS),
            ThresholdResult(evaluator="b", score=2.0, threshold=4.0, status=ThresholdStatus.FAIL),
        ]
        assert any_failures(results)
