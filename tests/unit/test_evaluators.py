"""Tests for continuous evaluation evaluators."""

from __future__ import annotations

from src.continuous_evaluation.evaluators import (
    ConcisenessEvaluator,
    get_all_evaluators,
    get_builtin_evaluators,
    get_custom_evaluators,
    get_safety_evaluators,
)

_MOCK_MODEL_CONFIG: dict[str, str] = {
    "azure_endpoint": "https://test.openai.azure.com/",
    "azure_deployment": "gpt-4o",
    "api_version": "2024-12-01-preview",
}

_MOCK_PROJECT_CONFIG: dict[str, str] = {
    "subscription_id": "00000000-0000-0000-0000-000000000000",
    "resource_group_name": "test-rg",
    "project_name": "test-project",
}


class TestConcisenessEvaluator:
    """Tests for the custom ConcisenessEvaluator."""

    def test_short_response_scores_high(self) -> None:
        evaluator = ConcisenessEvaluator()
        result = evaluator(response="This is a short, clear answer.")
        assert result["conciseness"] >= 4.0

    def test_long_response_scores_lower(self) -> None:
        evaluator = ConcisenessEvaluator()
        long_response = " ".join(["word"] * 300)
        result = evaluator(response=long_response)
        assert result["conciseness"] < 3.0

    def test_medium_response_scores_medium(self) -> None:
        evaluator = ConcisenessEvaluator()
        medium_response = " ".join(["word"] * 75)
        result = evaluator(response=medium_response)
        score = result["conciseness"]
        assert 2.0 <= score <= 5.0

    def test_empty_response(self) -> None:
        evaluator = ConcisenessEvaluator()
        result = evaluator(response="")
        assert "conciseness" in result


class TestEvaluatorGetters:
    """Tests for evaluator factory functions."""

    def test_get_builtin_evaluators_returns_dict(self) -> None:
        evaluators = get_builtin_evaluators(_MOCK_MODEL_CONFIG)
        assert isinstance(evaluators, dict)
        assert len(evaluators) > 0

    def test_get_safety_evaluators_returns_dict(self) -> None:
        evaluators = get_safety_evaluators(_MOCK_PROJECT_CONFIG)
        assert isinstance(evaluators, dict)
        assert len(evaluators) > 0

    def test_get_custom_evaluators_includes_conciseness(self) -> None:
        evaluators = get_custom_evaluators()
        assert "conciseness" in evaluators

    def test_get_all_evaluators_combines_all(self) -> None:
        all_evals = get_all_evaluators(_MOCK_MODEL_CONFIG, _MOCK_PROJECT_CONFIG)
        builtin = get_builtin_evaluators(_MOCK_MODEL_CONFIG)
        custom = get_custom_evaluators()
        # all_evaluators should contain at least builtin + custom keys
        for key in builtin:
            assert key in all_evals
        for key in custom:
            assert key in all_evals
