# Copilot Instructions — azure-ai-redteam-eval

## Project Purpose
Demo repo for a 15-min talk: **"Continuous Evaluation & Monitoring for AI Applications"**.  
**CE (Continuous Evaluation)** and **CM (Continuous Monitoring)** are the hero concepts.  
A multi-agent system built with the **Microsoft Agent Framework** serves as the application under evaluation.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+, async/await, type hints everywhere |
| Agent Framework | `agent-framework-azure-ai`, `agent-framework-core` (pre-release) |
| Evaluation SDK | `azure-ai-evaluation >= 1.0.0` |
| API | FastAPI + Uvicorn |
| Observability | OpenTelemetry + `azure-monitor-opentelemetry` |
| Config | Pydantic v2 + `pydantic-settings` + `python-dotenv` |
| IaC | Bicep only (no Terraform) — all in `infra/` |
| CI/CD | GitHub Actions (OIDC federated auth) |
| Package manager | `uv` (fallback: `pip`) |

---

## Key Directories

```
src/agents/                  # Multi-agent app (orchestrator, planner, retrieval, safety)
src/continuous_evaluation/   # ★ CE: run_evaluation.py, regression_check.py, thresholds.py
src/redteam/                 # ★ CE (adversarial): run_redteam.py, attack_strategies.py
src/continuous_monitoring/   # ★ CM: telemetry.py, eval_metrics_exporter.py, dashboards/
infra/                       # Bicep IaC: main.bicep + modules/
.github/workflows/           # ci.yml, deploy.yml, evaluate.yml, redteam.yml
docs/                        # ce-cm-lifecycle.md, architecture.md, talk-script.md
fallback/                    # Pre-baked demo outputs (safety net for live talk)
```

---

## Build & Test Commands

```bash
# Install deps
uv sync                          # or: pip install -r requirements.txt

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
pyright

# Tests
pytest tests/unit/
pytest tests/integration/

# Run evaluations
python -m src.continuous_evaluation.run_evaluation        # full eval
python -m src.continuous_evaluation.run_pr_evaluation     # PR lightweight eval
python -m src.continuous_evaluation.regression_check      # regression diff

# Red team
python -m src.redteam.run_redteam

# Makefile shortcuts (evaluate, redteam, regression-check, etc.)
make evaluate
make redteam
```

---

## Conventions

- **Agent classes**: subclass `Executor`, use `@handler` decorator; wire via `WorkflowBuilder`. Names: alphanumeric + hyphens, max 63 chars, no underscores.
- **Evaluation thresholds**: all pass/warn/fail values live in `src/continuous_evaluation/thresholds.py` — do not hardcode elsewhere.
- **Secrets**: always via managed identity + Key Vault; never hardcode keys or connection strings.
- **Telemetry**: every agent call and LLM invocation must emit structured OTel traces.
- **Bicep**: modular — `main.bicep` orchestrates `infra/modules/*.bicep`; use `.bicepparam` files, not JSON params.
- **Docstrings**: Google style, required on every public function and class.
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, `infra:`).
- **Code style**: `ruff format` (line length 120), `ruff check` with `["E","F","I","UP","B","SIM"]`.

---

## CI/CD Workflows

| Workflow | Trigger | CE/CM Role |
|----------|---------|------------|
| `ci.yml` | PR → `main` | Lint + tests + lightweight eval (5 rows) → PR summary |
| `deploy.yml` | push `main` / manual | Bicep deploy + smoke test |
| `evaluate.yml` | post-deploy / scheduled | Full eval + regression check — **blocks rollout on regression** |
| `redteam.yml` | weekly / manual | Adversarial probes — **fails on critical findings** |

---

## Environment Variables (see `.env.example`)

```
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_AI_FOUNDRY_PROJECT, AZURE_AI_FOUNDRY_ENDPOINT
APPLICATIONINSIGHTS_CONNECTION_STRING
AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_LOCATION=eastus2
LOG_LEVEL=INFO
```