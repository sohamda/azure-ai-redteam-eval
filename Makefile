# ============================================================
# azure-ai-redteam-eval — Makefile
# Convenient targets for demos, CI, and development.
# ============================================================

.DEFAULT_GOAL := help

# ---------- Setup ----------

.PHONY: install
install: ## Install all dependencies (including dev)
	uv sync --all-extras || pip install -e ".[dev]"

# ---------- Continuous Evaluation (CE) ----------

.PHONY: evaluate
evaluate: ## Run full Continuous Evaluation against golden dataset
	python -m src.continuous_evaluation.run_evaluation

.PHONY: evaluate-pr
evaluate-pr: ## Run lightweight Continuous Evaluation (PR subset — 5 rows)
	python -m src.continuous_evaluation.run_pr_evaluation

.PHONY: regression-check
regression-check: ## Compare current eval scores against baseline, detect regressions
	python -m src.continuous_evaluation.regression_check

.PHONY: redteam
redteam: ## Run AI red-team probes against the deployed agents
	python -m src.redteam.run_redteam

# ---------- Agent Demo ----------

.PHONY: agent-demo
agent-demo: ## Run the multi-agent orchestrator demo
	python -m src.app

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
	ruff check src/ tests/

.PHONY: format
format: ## Run ruff formatter
	ruff format src/ tests/

.PHONY: format-check
format-check: ## Check formatting without applying changes
	ruff format --check src/ tests/

.PHONY: typecheck
typecheck: ## Run pyright type checker
	pyright src/ tests/

# ---------- Tests ----------

.PHONY: test
test: ## Run all tests
	pytest tests/ -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Run integration tests only
	pytest tests/integration/ -v

# ---------- CI (all quality gates) ----------

.PHONY: ci
ci: lint format-check typecheck test-unit evaluate-pr ## Run all CI checks (lint + format + typecheck + unit tests + PR eval)

# ---------- Help ----------

.PHONY: help
help: ## Show this help message
	@powershell -NoProfile -Command "Get-Content $(MAKEFILE_LIST) | Select-String '^[a-zA-Z_-]+:.*?## ' | ForEach-Object { $$_ -match '^([a-zA-Z_-]+):.*?## (.*)$$' | Out-Null; Write-Host ('{0,-20} {1}' -f $$Matches[1], $$Matches[2]) }"
