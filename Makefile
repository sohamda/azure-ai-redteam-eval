# ============================================================
# azure-ai-redteam-eval — Makefile
# Convenient targets for demos, CI, and development.
# ============================================================

.DEFAULT_GOAL := help

# ---------- Python interpreter (prefer the project venv) ----------
# `make` does not inherit an activated venv, so resolve the interpreter
# explicitly to avoid falling back to a global Python that lacks the deps.
ifeq ($(OS),Windows_NT)
    PYTHON := $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python)
else
    PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python)
endif

# ---------- Setup ----------

.PHONY: install
install: ## Install all dependencies (including dev)
	uv sync --all-extras || pip install -e ".[dev]"

# ---------- Continuous Evaluation (CE) ----------

.PHONY: evaluate
evaluate: ## Run full Continuous Evaluation against golden dataset
	$(PYTHON) -m src.continuous_evaluation.run_evaluation

.PHONY: evaluate-pr
evaluate-pr: ## Run lightweight Continuous Evaluation (PR subset — 5 rows)
	$(PYTHON) -m src.continuous_evaluation.run_pr_evaluation

.PHONY: regression-check
regression-check: ## Compare current eval scores against baseline, detect regressions
	$(PYTHON) -m src.continuous_evaluation.regression_check

.PHONY: demo-regression
demo-regression: ## DEMO: show CE blocking a regressed run (staged, no Azure calls)
	@echo ">>> Simulating a code change that dropped groundedness. Running the same gate CI runs..."
	-$(PYTHON) -m src.continuous_evaluation.regression_check --current fallback/regressed_scores.json --output regression_comparison.md
	@echo ""
	@echo ">>> Exit code 1 — in CI this BLOCKS the deployment. That is Continuous Evaluation catching a regression before users do."

.PHONY: redteam
redteam: ## Run AI red-team probes against the deployed agents
	$(PYTHON) -m src.redteam.run_redteam

# ---------- Agent Demo ----------

.PHONY: agent-demo
agent-demo: ## Run the multi-agent orchestrator demo
	$(PYTHON) -m src.app

# ---------- Infrastructure ----------

.PHONY: deploy
deploy: ## Deploy Azure infrastructure via Bicep
	az deployment group create --resource-group $(AZURE_RESOURCE_GROUP) --template-file infra/main.bicep --parameters infra/parameters/dev.bicepparam

.PHONY: deploy-prod
deploy-prod: ## Deploy production Azure infrastructure via Bicep
	az deployment group create --resource-group $(AZURE_RESOURCE_GROUP) --template-file infra/main.bicep --parameters infra/parameters/prod.bicepparam

# ---------- Code Quality ----------

.PHONY: lint
lint: ## Run ruff linter
	$(PYTHON) -m ruff check src/ tests/

.PHONY: format
format: ## Run ruff formatter
	$(PYTHON) -m ruff format src/ tests/

.PHONY: format-check
format-check: ## Check formatting without applying changes
	$(PYTHON) -m ruff format --check src/ tests/

.PHONY: typecheck
typecheck: ## Run pyright type checker
	$(PYTHON) -m pyright src/ tests/

# ---------- Tests ----------

.PHONY: test
test: ## Run all tests
	$(PYTHON) -m pytest tests/ -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	$(PYTHON) -m pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Run integration tests only
	$(PYTHON) -m pytest tests/integration/ -v

# ---------- CI (all quality gates) ----------

.PHONY: ci
ci: lint format-check typecheck test-unit evaluate-pr ## Run all CI checks (lint + format + typecheck + unit tests + PR eval)

# ---------- Help ----------

.PHONY: help
help: ## Show this help message
	@powershell -NoProfile -Command "Get-Content $(MAKEFILE_LIST) | Select-String '^[a-zA-Z_-]+:.*?## ' | ForEach-Object { $$_ -match '^([a-zA-Z_-]+):.*?## (.*)$$' | Out-Null; Write-Host ('{0,-20} {1}' -f $$Matches[1], $$Matches[2]) }"
