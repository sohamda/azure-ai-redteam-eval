# Tasks — azure-ai-redteam-eval

> Implementation plan for a 15-minute talk: **Continuous Evaluation & Monitoring for AI Applications**.
> CE/CM is the hero; the multi-agent system is the subject being evaluated and monitored.

---

## Phase 0: Foundation & Configuration ✅

- [x] **0.1** Update `.github/copilot-instructions.md` — rename sections, add `ci.yml`, rename folders to `continuous_evaluation/` and `continuous_monitoring/`, update Mermaid diagrams and Done checklist
- [x] **0.2** Create `.gitignore` — Python, Node, IDE, `.env`, `__pycache__`, `.ruff_cache`, etc.
- [x] **0.3** Create `.env.example` — template for all required env vars
- [x] **0.4** Create `pyproject.toml` — project metadata, dependencies, ruff + pyright config
- [x] **0.5** Create `requirements.txt` — pinned dependencies
- [x] **0.6** Create `Makefile` — targets: `install`, `agent-demo`, `evaluate`, `evaluate-pr`, `redteam`, `regression-check`, `deploy`, `test`, `lint`, `format`, `typecheck`, `ci`

---

## Phase 1: Documentation & Diagrams (the "presentation layer") ✅

- [x] **1.1** Create `README.md` — leads with CE/CM, hero lifecycle Mermaid diagram, "What is CE?", "What is CM?", quick-start (evaluate → redteam → dashboard → agents), repo structure, prerequisites
- [x] **1.2** Create `docs/ce-cm-lifecycle.md` — CE/CM lifecycle loop Mermaid diagram with detailed explanation per stage
- [x] **1.3** Create `docs/architecture.md` — full architecture Mermaid (CI/CD → infra → agents → eval → monitoring) narrated through CE/CM lens
- [x] **1.4** Create `docs/talk-script.md` — minute-by-minute speaker notes matching the revised talk timeline

---

## Phase 2: Application Config & Entrypoint ✅

- [x] **2.1** Create `src/__init__.py`
- [x] **2.2** Create `src/config.py` — Pydantic settings: Azure OpenAI, AI Foundry, App Insights, thresholds
- [x] **2.3** Create `src/app.py` — FastAPI entrypoint with `/chat` endpoint that invokes the orchestrator

---

## Phase 3: Multi-Agent System (the "application under evaluation") ✅

- [x] **3.1** Create `src/agents/__init__.py`
- [x] **3.2** Create `src/agents/orchestrator.py` — Agent Framework `WorkflowBuilder` wiring Planner → Retrieval → Safety via `Executor` subclasses; must fit in ~40 lines of core logic
- [x] **3.3** Create `src/agents/planner_agent.py` — plans tasks, delegates to other agents
- [x] **3.4** Create `src/agents/retrieval_agent.py` — RAG / grounding agent
- [x] **3.5** Create `src/agents/safety_agent.py` — content-safety guardrail agent
- [x] **3.6** Create `src/agents/plugins/__init__.py`
- [x] **3.7** Create `src/agents/plugins/search_plugin.py` — Agent Framework search plugin
- [x] **3.8** Create `src/agents/plugins/eval_plugin.py` — plugin to trigger inline evaluation

---

## Phase 4: Continuous Evaluation (CE) — the hero ✅

- [x] **4.1** Create `src/continuous_evaluation/__init__.py`
- [x] **4.2** Create `src/continuous_evaluation/thresholds.py` — central pass/warn/fail threshold definitions per evaluator
- [x] **4.3** Create `src/continuous_evaluation/evaluators.py` — built-in (Groundedness, Coherence, Relevance, Fluency) + safety (ContentSafety, ProtectedMaterial) + at least one custom evaluator
- [x] **4.4** Create `src/continuous_evaluation/run_evaluation.py` — full eval entry point: loads golden dataset, runs all evaluators, applies thresholds, outputs results JSON + summary table
- [x] **4.5** Create `src/continuous_evaluation/run_pr_evaluation.py` — lightweight PR eval: small dataset subset, fast, outputs to stdout for `$GITHUB_STEP_SUMMARY`
- [x] **4.6** Create `src/continuous_evaluation/regression_check.py` — compares current scores against stored baseline, detects regressions, outputs before/after diff
- [x] **4.7** Create `src/continuous_evaluation/score_tracker.py` — logs eval scores as App Insights custom metrics (bridges CE → CM)
- [x] **4.8** Create `src/continuous_evaluation/metrics.py` — parse & format evaluation results into tables
- [x] **4.9** Create `src/continuous_evaluation/datasets/eval_golden.jsonl` — full golden eval dataset (10–15 rows)
- [x] **4.10** Create `src/continuous_evaluation/datasets/eval_golden_small.jsonl` — PR subset (5 rows)
- [x] **4.11** Create `src/continuous_evaluation/datasets/adversarial_prompts.jsonl` — red-team prompt dataset

---

## Phase 5: Red Teaming (part of CE) ✅

- [x] **5.1** Create `src/redteam/__init__.py`
- [x] **5.2** Create `src/redteam/run_redteam.py` — entry point: invokes AdversarialSimulator with attack categories, captures results
- [x] **5.3** Create `src/redteam/attack_strategies.py` — prompt injection, jailbreak, PII extraction, harmful-content patterns
- [x] **5.4** Create `src/redteam/report.py` — generate JSON + markdown report with pass/fail per category and severity levels

---

## Phase 6: Continuous Monitoring (CM) ✅

- [x] **6.1** Create `src/continuous_monitoring/__init__.py`
- [x] **6.2** Create `src/continuous_monitoring/telemetry.py` — OpenTelemetry + App Insights setup; instrument every agent call, LLM invocation, eval run
- [x] **6.3** Create `src/continuous_monitoring/eval_metrics_exporter.py` — exports eval scores as OTel metrics to App Insights (makes eval scores monitorable)
- [x] **6.4** Create `src/continuous_monitoring/alert_rules.py` — defines alert conditions: score drop, latency spike, safety flag rate
- [x] **6.5** Create `src/continuous_monitoring/dashboards/ce_cm_dashboard.json` — Azure Workbook with 3 sections: Evaluation Trends, Agent Health, Alerts & Regressions

---

## Phase 7: Infrastructure as Code (Bicep) ✅

- [x] **7.1** Create `infra/modules/managed-identity.bicep` — user-assigned managed identity + scoped RBAC
- [x] **7.2** Create `infra/modules/key-vault.bicep` — Key Vault for secrets
- [x] **7.3** Create `infra/modules/openai.bicep` — Azure OpenAI resource + GPT-4o deployment
- [x] **7.4** Create `infra/modules/ai-foundry.bicep` — Azure AI Foundry hub + project
- [x] **7.5** Create `infra/modules/app-service.bicep` — App Service (or Container App) for agent host
- [x] **7.6** Create `infra/modules/monitoring.bicep` — Application Insights + Log Analytics workspace
- [x] **7.7** Create `infra/modules/alerts.bicep` — Azure Monitor alert rules (score drop, latency, safety flags) as IaC
- [x] **7.8** Create `infra/main.bicep` — orchestrator calling all modules
- [x] **7.9** Create `infra/parameters/dev.bicepparam` — dev environment parameters
- [x] **7.10** Create `infra/parameters/prod.bicepparam` — prod environment parameters

---

## Phase 8: CI/CD Workflows (GitHub Actions) ✅

- [x] **8.1** Create `.github/workflows/ci.yml` — PR gate: lint + typecheck + unit tests + lightweight eval → post scores to `$GITHUB_STEP_SUMMARY`
- [x] **8.2** Create `.github/workflows/deploy.yml` — push to main: OIDC login → Bicep lint → deploy (incl. alerts.bicep) → smoke test
- [x] **8.3** Create `.github/workflows/evaluate.yml` — post-deploy: full eval → regression check → score tracking → upload artifact → fail if regression
- [x] **8.4** Create `.github/workflows/redteam.yml` — manual + weekly: red-team probes → upload report → fail if critical findings

---

## Phase 9: Tests ✅

- [x] **9.1** Create `tests/__init__.py`
- [x] **9.2** Create `tests/unit/__init__.py`
- [x] **9.3** Create `tests/unit/test_evaluators.py` — unit tests for custom evaluators and threshold logic
- [x] **9.4** Create `tests/unit/test_regression_check.py` — unit tests for regression detection
- [x] **9.5** Create `tests/unit/test_thresholds.py` — unit tests for threshold pass/warn/fail logic
- [x] **9.6** Create `tests/integration/__init__.py`
- [x] **9.7** Create `tests/integration/test_agent_flow.py` — end-to-end agent orchestration test

---

## Phase 10: Fallback Outputs (Pre-Baked Demo Safety Net) ✅

- [x] **10.1** Create `fallback/evaluation_results.json` — pre-baked full eval output
- [x] **10.2** Create `fallback/regression_comparison.md` — pre-baked before/after score diff
- [x] **10.3** Create `fallback/redteam_report.md` — pre-baked red-team report
- [x] **10.4** Create `fallback/agent_demo_output.txt` — pre-baked agent interaction log

---

## Phase 11: Final Validation

- [x] **11.1** Run `make lint` + `make typecheck` — zero errors
- [x] **11.2** Run `make test` — all unit tests pass (31/31)
- [x] **11.3** Run `make agent-demo` — agents respond end-to-end (FastAPI + /chat + chat UI at http://localhost:8000)
- [x] **11.4** Run `make evaluate` — scores output cleanly (groundedness 4.70, coherence 4.00, relevance 4.60, fluency 4.10, conciseness 4.95 — all above thresholds)
- [x] **11.5** Run `make redteam` — report generates (10 probes, 6 categories, 100% blocked with RedTeam SDK + custom probes)
- [x] **11.6** Run `make regression-check` — comparison outputs (no regressions vs. baseline)
- [x] **11.7** All Mermaid diagrams render correctly (verified in README, docs/ce-cm-lifecycle.md, docs/architecture.md)
- [x] **11.8** Documentation updated with actual scores and verified demo commands
- [x] **11.9** Fallback files updated with real demo outputs

---

## ✅ Project Complete

All 11 phases done. The repo is fully implemented, tested, and ready for the 15-minute talk.

**Verified capabilities:**
- Multi-agent chat service (FastAPI + chat UI + OpenTelemetry instrumentation)
- Full Continuous Evaluation pipeline (5 evaluators, 10-row golden dataset, threshold gating, regression detection)
- AI Red Teaming (Azure AI Evaluation RedTeam SDK + custom adversarial probes, 100% blocked)
- Continuous Monitoring (OTel → App Insights, eval scores as metrics, alert rules, Azure Workbook dashboard)
- Infrastructure as Code (7 Bicep modules, dev/prod parameter files)
- CI/CD (4 GitHub Actions workflows: ci, deploy, evaluate, redteam)
- 31 unit tests passing

---

## Implementation Order (Recommended)

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 3  →  Phase 4  →  Phase 5
                                                     ↓
Phase 10 ←  Phase 9  ←  Phase 8  ←  Phase 7  ←  Phase 6
                                                     ↓
                                                 Phase 11
```

Start with foundation (Phase 0), then docs/diagrams (Phase 1) so the "presentation" backbone exists early. Build the app (Phases 2-3), then the CE/CM/red-team code (Phases 4-6), then infra + CI/CD (Phases 7-8), then tests + fallbacks (Phases 9-10). Validate everything in Phase 11.
