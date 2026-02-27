# Talk Script — Continuous Evaluation & Monitoring for AI Applications

> 15-minute informal meetup talk. No slides — everything from the GitHub repo (Mermaid diagrams, code, terminal, Azure Portal). Pre-baked fallbacks in `fallback/` if live demo stalls.
>
> **Status: All demos verified and running.** Evaluation scores, red-team probes, and agent endpoints are live.

---

## Pre-Show Setup

- [x] Azure resources deployed and warm (`make deploy` 30+ min before)
- [x] `.env` populated, `az login` done
- [x] Agent service tested (`make agent-demo` → http://localhost:8000 with chat UI)
- [x] Evaluation run verified (`make evaluate` → all thresholds pass)
- [x] Red team run verified (`make redteam` → 10/10 probes blocked)
- [ ] Browser tabs: (1) GitHub repo README, (2) `docs/architecture.md`, (3) GitHub Actions tab, (4) Azure Portal → App Insights → Dashboard
- [ ] Terminal tabs pre-named: "Agent Demo", "Evaluation", "Red Team"
- [ ] Font size: browser zoom 150%+, terminal font 18pt+
- [ ] Fallback files verified in `fallback/`

---

## Timeline

### 0:00–0:30 — Hook

**What you say:**
> "How many of you have CI/CD for your apps? *(hands go up)* Now — how many of you evaluate the *quality* of your AI responses before shipping? *(fewer hands)* Let me show you what that looks like. Everything I'm about to show lives in one GitHub repo."

**What's on screen:** Browser — GitHub repo landing page, `README.md` visible.

---

### 0:30–2:00 — CE/CM Lifecycle (the Hero Diagram)

**What you do:** Scroll to the CE/CM lifecycle Mermaid diagram in `README.md`. Walk through the loop.

**What you say:**
> "This is the Continuous Evaluation and Continuous Monitoring lifecycle. Every code change goes through a lightweight eval on the PR — if it fails, you can't merge. After deploy, a full evaluation runs against a golden dataset. If scores regress — the rollout is blocked. In production, monitoring watches for drift and anomalies. When something goes wrong, it feeds back into new eval cases. The loop never stops."

**Key points to hit:**
- CE = every change is evaluated before reaching users
- CM = production is monitored for quality drift in real time
- They feed each other — it's a loop, not a one-shot

---

### 2:00–3:30 — Architecture Walkthrough

**What you do:** Click into `docs/architecture.md`. GitHub renders the full Mermaid diagram.

**What you say:**
> "Here's the full architecture. Four GitHub Actions workflows — one gates PRs, one deploys, one runs full evaluation, one does red-team probes. The multi-agent system here *(point)* is just the app being evaluated — it's not the star. The star is this: Continuous Evaluation and Continuous Monitoring, with eval scores flowing into App Insights and alerts firing when quality drops."

**Spend ~20 seconds per subgraph.** Don't deep-dive into agent details.

---

### 3:30–4:30 — Repo Tour

**What you do:** Click back to repo root. Point at the folder structure.

**What you say:**
> "Notice the folder names — `continuous_evaluation`, `continuous_monitoring`. These aren't afterthoughts. They're the core of the repo. The `agents/` folder is the application under test. Let me show you each of these running."

---

### 4:30–6:00 — Demo 1: Multi-Agent Interaction (Brief)

**What you do:** Switch to terminal. Run `make agent-demo` (starts FastAPI at http://localhost:8000).

**What you say:**
> "Here's the agent system. Open the browser to localhost:8000 — there's a chat UI. A user sends a question. The orchestrator delegates to a planner, a retrieval agent for grounding, and a safety agent for guardrails. *(point at agent turns in output)* This is a standard multi-agent pattern — Microsoft Agent Framework under the hood, with a direct Azure OpenAI fallback. But this isn't the point of the talk. The point is: how do you know this is *good*?"

**Fallback:** If slow, open `fallback/agent_demo_output.txt` on GitHub.

**Keep this to 90 seconds max.** Transition immediately.

---

### 6:00–9:00 — Demo 2: Continuous Evaluation (The Centerpiece)

**What you do:** Terminal — run `make evaluate`.

**What you say:**
> "This is Continuous Evaluation. I'm running the full eval against our golden dataset — 10 rows, real queries, expected answers. The SDK runs Groundedness, Coherence, Relevance, Fluency, and Conciseness evaluators."

*(Wait for scores to print)*

> "Here are the scores. Groundedness 4.7, Coherence 4.0, Relevance 4.6, Fluency 4.1, Conciseness 4.95. Every one of these has a threshold — minimum 4.0 for quality metrics. If any score drops below the threshold, the pipeline fails. No human judgment needed."

**Then click into GitHub:**

1. Open `src/continuous_evaluation/run_evaluation.py` — "Here's the evaluator wiring. ~20 lines."
2. Open `src/continuous_evaluation/thresholds.py` — "Here are the thresholds. Configurable per evaluator."
3. Open `src/continuous_evaluation/regression_check.py` — "This compares current scores against the last baseline. Regressions block deployment."
4. Open `.github/workflows/evaluate.yml` — "And here's the workflow. Runs after every deploy. Fails if regression."

**Fallback:** If eval is slow, open `fallback/evaluation_results.json` on GitHub.

---

### 9:00–11:00 — Demo 3: Red Teaming (Part of CE)

**What you do:** Terminal — run `make redteam`.

**What you say:**
> "Red teaming is adversarial evaluation. We fire prompt injection, jailbreak, and PII extraction attacks against the agents. *(point at attack categories in output)* 10 probes, 6 categories, 100% blocked. Here's the report — pass/fail per category. Critical findings block deployment."

**Then click into GitHub:**

1. Open `src/redteam/run_redteam.py` — "Uses the Azure AI Evaluation Red Team SDK with Baseline and Jailbreak strategies, plus custom probes."
2. Open `.github/workflows/redteam.yml` — "Runs weekly. Fails on critical findings."

**Fallback:** Open `fallback/redteam_report.md` on GitHub.

---

### 11:00–13:00 — Demo 4: Continuous Monitoring

**What you do:** Switch to browser — Azure Portal → Application Insights → Dashboard.

**What you say:**
> "Now we're in production. Continuous Monitoring. This dashboard has three sections."
> 
> **Section 1 — Evaluation Trends:** "Groundedness, Coherence, Relevance, Safety scores over time. Every eval run pushes scores as custom metrics. You can see trends — and spot when something degraded."
>
> **Section 2 — Agent Health:** "Latency P50/P95/P99 per agent, error rates, token usage. Standard observability, applied to AI agents."
>
> **Section 3 — Alerts & Regressions:** "Alert rules fire when scores drop, latency spikes, or safety flags exceed thresholds. These alerts are deployed as IaC — in the same Bicep as the rest of the infra."

**Fallback:** If portal is slow, open `src/continuous_monitoring/dashboards/ce_cm_dashboard.json` on GitHub and describe the metrics.

---

### 13:00–14:00 — The CI/CD Pipeline

**What you do:** Back to GitHub. Click into `.github/workflows/`. Show all four files.

**What you say:**
> "Four workflows. `ci.yml` gates every PR with lint, tests, and a lightweight eval. `deploy.yml` deploys the Bicep infra. `evaluate.yml` runs full eval plus regression check. `redteam.yml` runs weekly."

Open the **Actions** tab — show a recent green run.

> "On every push: deploy, evaluate, check for regression. If anything fails — no ship. This is CI/CD for AI."

If you have a merged PR: open it, click into the CI check, show the eval scores in `$GITHUB_STEP_SUMMARY`.

---

### 14:00–14:45 — Takeaway

**What you do:** Scroll back to `README.md` — point to the "Key Takeaway" section at the bottom.

**What you say:**
> "GenAI apps aren't special — they just need more gates. Deploy, Evaluate, Monitor, Improve. The loop never stops. Add Continuous Evaluation and Continuous Monitoring to your pipelines today. The tooling exists — `azure-ai-evaluation`, OpenTelemetry, Application Insights, GitHub Actions. Fork this repo and try it."

---

### 14:45–15:00 — Close

**What you say:**
> "Everything you saw is in this repo. Star it, fork it, break it. Questions?"

**What's on screen:** GitHub repo landing page.

---

## Emergency Fallbacks

| Demo | Live Command | Fallback File |
|------|-------------|---------------|
| Agent Demo | `make agent-demo` | `fallback/agent_demo_output.txt` |
| Evaluation | `make evaluate` | `fallback/evaluation_results.json` |
| Regression Check | `make regression-check` | `fallback/regression_comparison.md` |
| Red Teaming | `make redteam` | `fallback/redteam_report.md` |
| Dashboard | Azure Portal | Describe `ce_cm_dashboard.json` metrics on GitHub |

## Timing Checkpoints

| Checkpoint | Expected Time | If Behind |
|------------|--------------|-----------|
| Finish lifecycle diagram | 2:00 | Skip architecture deep-dive, go straight to repo tour |
| Start agent demo | 4:30 | Cut agent demo to 60s |
| Start evaluation demo | 6:00 | Use fallback output if eval takes > 90s |
| Start red-team demo | 9:00 | If at 9:30+, show fallback report only |
| Start monitoring demo | 11:00 | If at 12:00+, skip dashboard, describe verbally |
| Start takeaway | 14:00 | Must hit this — skip CI/CD section if needed |
