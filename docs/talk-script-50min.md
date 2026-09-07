# Talk Script (50 min) — Continuous Evaluation & Monitoring for AI Applications

> **Techorama conference session.** ~50 minutes + Q&A. **No slides** — everything is driven live from the GitHub repo (Mermaid diagrams, code, terminal, Azure Portal). Pre-baked fallbacks in `fallback/` if a live demo stalls.
>
> This is the **long-form** version. For the 15-minute lightning variant, use [talk-script.md](talk-script.md).
>
> **Core message:** GenAI apps need the same CI/CD rigour as traditional apps — *plus* Continuous Evaluation (CE) and Continuous Monitoring (CM). CE gates quality before ship; CM watches quality in production; the two form a loop.

---

## Pre-Show Setup (do 30+ min before)

- [ ] Azure resources deployed and warm (`make deploy`), `.env` populated, `az login` done
- [ ] `az account show` confirms the right subscription
- [ ] Agent service tested (`make agent-demo` → http://localhost:8000 chat UI)
- [ ] Full eval verified (`make evaluate` → all thresholds pass)
- [ ] **Regression demo verified (`make demo-regression` → RED, exit 1)** ← new for this version
- [ ] Red team verified (`make redteam` → probes blocked)
- [ ] **Backup screen-recordings** of each demo saved locally (conference wifi + live LLM latency is risky)
- [ ] Browser tabs open, in order:
  1. GitHub repo `README.md`
  2. `docs/architecture.md`
  3. `docs/ce-cm-lifecycle.md`
  4. GitHub → Actions tab (a recent green run)
  5. A merged PR showing eval scores in the Checks summary
  6. Azure Portal → Application Insights → the CE/CM dashboard
- [ ] Terminal tabs pre-named: "Agent", "Evaluate", "Regression", "Red Team"
- [ ] Browser zoom 150%+, terminal font 22pt+ (big room, back row must read it)
- [ ] Water. Confidence monitor showing the timer.

---

## Act Map (50 min)

| Act | Topic | Time | Running total |
|-----|-------|------|---------------|
| 1 | Hook + the pain (why CE/CM exists) | 7 min | 0:00–7:00 |
| 2 | The CE/CM lifecycle + architecture | 8 min | 7:00–15:00 |
| 3 | The app under test (brief agent demo) | 5 min | 15:00–20:00 |
| 4 | **Continuous Evaluation** — the centerpiece | 12 min | 20:00–32:00 |
| 5 | Red teaming — adversarial CE (two phases) | 7 min | 32:00–39:00 |
| 6 | **Continuous Monitoring** — production loop | 6 min | 39:00–45:00 |
| 7 | CI/CD wiring + takeaway | 5 min | 45:00–50:00 |
| — | Q&A | ~10 min | 50:00+ |

---

## Act 1 — Hook + the pain (0:00–7:00)

**The pain story (tell it, don't rush):**

> "Show of hands — who here has CI/CD for their apps? *(most hands)* Keep them up if that pipeline also checks whether your AI's *answers* are any good. *(most hands drop)* That gap is what this talk is about.
>
> Here's a story you'll recognise. A team ships a small prompt tweak — 'be more helpful.' Tests pass. Lint passes. It deploys. Two weeks later a customer notices the assistant is confidently making things up. The prompt change had quietly dropped groundedness by 15%. Nothing failed. No alert fired. No test was red. Because **none of their gates could see quality.**
>
> Traditional software fails loudly — a stack trace, a 500. GenAI fails *silently and plausibly*. A wrong answer looks exactly like a right answer. That's the whole problem."

**The reframe:**

> "So we need two new habits. **Continuous Evaluation** — every change is scored for quality *before* it reaches users, and a regression blocks the ship, exactly like a failing unit test. **Continuous Monitoring** — production is watched for quality drift in real time, and what we learn there becomes new test cases. Everything I show is in one public repo. No slides — it's all code and terminals."

**On screen:** GitHub repo `README.md`. Point at the two badges (CE thresholds, red team) and the lifecycle diagram teaser.

> *Transition:* "Let me show you the loop first, then we'll run every piece of it live."

---

## Act 2 — The CE/CM lifecycle + architecture (7:00–15:00)

**On screen:** [docs/ce-cm-lifecycle.md](ce-cm-lifecycle.md) — the hero Mermaid diagram.

Walk the loop, ~30s per hop:

> "A change opens a PR. `ci.yml` runs a **lightweight eval** on a small dataset — if a score is under threshold, the PR can't merge. Merge triggers deploy. After deploy, `evaluate.yml` runs the **full evaluation** against a golden dataset and a **regression check** against the last known-good baseline. Regression? Rollout blocked, alert fired. Clean? It serves production traffic — and every request emits telemetry. **Continuous Monitoring** watches eval scores, latency, safety flags. An anomaly becomes an investigation, which becomes a **new row in the golden dataset** — and we're back at the top. The loop never ends."

**Then switch to** [docs/architecture.md](architecture.md):

> "Same story, wider lens. Four GitHub Actions workflows on the left. Azure infra in the middle — OpenAI, AI Foundry, App Insights, all Bicep. The multi-agent app is *the thing being evaluated* — deliberately not the star. The star is these two subgraphs: **Continuous Evaluation** feeding scores in, **Continuous Monitoring** turning those scores into metrics and alerts."

**Say the honest positioning line early (an expert audience is already thinking it):**

> "You might ask: doesn't Azure AI Foundry now have built-in continuous and online evaluation? It does, and it's great. What this repo shows is the *portable, CI-gating* version — evaluators as code, thresholds in version control, regressions failing a GitHub Action. Use the platform feature, this pattern, or both. The *discipline* is the point, not the vendor button."

> *Transition:* "Here's the app we're going to grade."

---

## Act 3 — The app under test (15:00–20:00)

**On screen:** terminal "Agent" → `make agent-demo`, then browser http://localhost:8000.

> "A multi-agent assistant on the Microsoft Agent Framework. Orchestrator routes through a **planner**, a **retrieval** agent for grounding, and a **safety** agent for guardrails. Send it a real question…"

Type in the chat UI: *"What are the best practices for deploying AI apps to Azure?"* Point at the agents involved in the response.

> "Standard pattern — and honestly, the framework choice doesn't matter for this talk. What matters is the question we can't answer by looking at it: **is this response actually good?** You can't eyeball that at scale. That's what evaluation is for."

**Fallback:** [fallback/agent_demo_output.txt](../fallback/agent_demo_output.txt). Keep this act tight — 5 min max.

> *Transition:* "Let's grade it. Objectively. Repeatably."

---

## Act 4 — Continuous Evaluation, the centerpiece (20:00–32:00)

### 4a. Run the full eval (20:00–24:00)

**On screen:** terminal "Evaluate" → `make evaluate` (or scroll to a pre-run result if the room's network is slow).

> "This runs the `azure-ai-evaluation` SDK against our **golden dataset** — real queries with expected answers. It scores five quality dimensions — **Groundedness, Coherence, Relevance, Fluency** — plus a **custom Conciseness** evaluator. It *also* runs two safety evaluators, content safety and protected material, against the same data."

When scores print:

> "Every score has a threshold — 4.0 for the quality metrics. Under threshold, the pipeline fails. No human in the loop, no vibes — a number and a gate."

Open the code, briefly:
- [src/continuous_evaluation/evaluators.py](../src/continuous_evaluation/evaluators.py) — "Here's the evaluator registry. Built-in, safety, and custom."
- **Call out the custom evaluator honestly:** "Conciseness is our custom one. It's an **LLM-as-judge** — it prompts the model to score 1–5 with a reason. If no judge model is configured, it degrades to a word-count heuristic so CI never hangs. This is the extension point: *your* domain metric — 'did it cite a policy number?', 'is the tone on-brand?' — lives right here."
- [src/continuous_evaluation/thresholds.py](../src/continuous_evaluation/thresholds.py) — "Thresholds, centralised, env-overridable. Never hardcoded in the runner."

### 4b. The money shot — a regression gets BLOCKED (24:00–30:00)

> "Green is nice, but green proves nothing. The real question is: **does the gate actually stop a bad change?** Let me break it on purpose."

**On screen:** terminal "Regression" → `make demo-regression`.

> "Imagine I just merged a prompt change. Here's the score set it produced — groundedness fell from 4.7 to 3.2. This runs the *exact same regression check CI runs*, comparing against our last known-good baseline."

When the red table prints and it exits non-zero:

> "There it is. **Groundedness — REGRESSION.** Exit code 1. In CI, this line is the difference between shipping a hallucinating assistant and stopping it at the door. *This* is Continuous Evaluation earning its name. Nobody had to notice. The pipeline noticed."

Open [src/continuous_evaluation/regression_check.py](../src/continuous_evaluation/regression_check.py) — "Current vs. baseline, delta beyond a threshold fails the build" — and [.github/workflows/evaluate.yml](../.github/workflows/evaluate.yml) — "and here it is wired to run after every deploy."

**Fallback:** [fallback/regression_comparison_blocked.md](../fallback/regression_comparison_blocked.md).

### 4c. Where scores go (30:00–32:00)

Open [src/continuous_evaluation/score_tracker.py](../src/continuous_evaluation/score_tracker.py):

> "Every eval run also pushes scores to Application Insights as custom metrics. That's the bridge from CE into CM — hold that thought, we'll see it on a dashboard in a few minutes."

> *Transition:* "Quality is one axis. Safety is another. For that we get adversarial."

---

## Act 5 — Red teaming, adversarial CE (32:00–39:00)

**On screen:** terminal "Red Team" → `make redteam`.

> "Red teaming is evaluation with an attacker's mindset. This runs in **two phases** — be precise about this, because they use different taxonomies."

**Phase 1 — the SDK scan:**

> "First, the **Azure AI Evaluation Red Team SDK**. Microsoft's service generates attack objectives across four **risk categories** — Violence, Hate/Unfairness, Sexual, Self-Harm — and applies attack strategies like Baseline and Jailbreak. This is service-side, automated adversarial generation."

**Phase 2 — the custom probes (this is the table you'll see):**

> "Second, our own curated probes — ten attacks across six **application-specific** categories: prompt injection, jailbreak, PII extraction, harmful content, social engineering, misinformation. The report table you're looking at is *this* phase."

Point at the pass/fail-by-category table.

> "Each probe checks whether the safety agent refused. Critical-severity failures fail the workflow."

Open [src/redteam/run_redteam.py](../src/redteam/run_redteam.py) (show the two phases) and [.github/workflows/redteam.yml](../.github/workflows/redteam.yml) ("runs weekly, and on demand").

**Be honest if asked how 'blocked' is judged** (see Q&A): the custom-probe detector is a keyword/refusal heuristic — good enough for a gate signal, but production should score refusals with a model, and the SDK phase already does the heavier lifting.

**Fallback:** [fallback/redteam_report.md](../fallback/redteam_report.md).

> *Transition:* "We've gated quality and safety before shipping. Now — production."

---

## Act 6 — Continuous Monitoring (39:00–45:00)

**On screen:** Azure Portal → Application Insights → the CE/CM dashboard.

> "In production, every agent call and LLM invocation emits an OpenTelemetry span into Application Insights. Three panels."

- **Evaluation Trends:** "Groundedness, coherence, relevance, safety — *over time*. Remember those eval scores we pushed as metrics? Here they are as a timeline. You can literally see the day a regression landed."
- **Agent Health:** "Latency P50/P95/P99 per agent, error rate, token usage. Classic observability, applied to agents — and token usage is also your cost signal."
- **Alerts & Regressions:** "Alert rules — score drop, latency spike, safety-flag rate — and they're **deployed as IaC** in the same Bicep as everything else."

Open [infra/modules/alerts.bicep](../infra/modules/alerts.bicep) briefly:

> "Alerts aren't clicked into a portal and forgotten. They're code, reviewed in PRs, versioned like the rest of the system."

**Close the loop explicitly:**

> "And here's the whole point. A monitoring anomaly triggers an investigation. The finding becomes a **new row in the golden dataset**. Which the next PR is evaluated against. CE feeds CM; CM feeds CE. The system gets *safer every iteration* — automatically."

**Fallback:** describe [src/continuous_monitoring/dashboards/ce_cm_dashboard.json](../src/continuous_monitoring/dashboards/ce_cm_dashboard.json) if the portal is slow.

---

## Act 7 — CI/CD wiring + takeaway (45:00–50:00)

**On screen:** GitHub → `.github/workflows/`, then the Actions tab (a green run), then a merged PR's Checks summary showing eval scores.

> "Four workflows tie it together. `ci.yml` gates every PR with lint, tests, and a lightweight eval. `deploy.yml` ships the Bicep. `evaluate.yml` runs full eval plus regression check. `redteam.yml` runs weekly. On a real PR, the eval scores show up right in the Checks tab — reviewers see quality next to the diff."

**The takeaway (land it slowly):**

> "GenAI apps aren't magic and they aren't exempt. They just need *more gates*. **Deploy. Evaluate. Monitor. Improve.** The loop never stops. The tooling already exists — `azure-ai-evaluation`, OpenTelemetry, Application Insights, GitHub Actions. Everything you saw is in this repo. Fork it, break it, add your own evaluator. That's the assignment. Thank you."

**On screen for Q&A:** repo landing page (offer to drop the URL / a QR in chat).

---

## Q&A — anticipated questions (rehearse these)

**"Why not just use Azure AI Foundry's built-in continuous / online evaluation?"**
> Use it — it's excellent for online, sampled, in-production eval. This repo's angle is *CI-gating and portability*: evaluators and thresholds as version-controlled code that fail a GitHub Action before deploy. They're complementary — platform online-eval for production sampling, this pattern for the pipeline gate.

**"What does continuous evaluation cost?"**
> It's LLM calls. A lightweight PR eval is a handful of rows × a few evaluators — cents. A full run is the golden dataset × evaluators (each judge is a model call). Control it by keeping PR datasets small, running the full set post-deploy/nightly, and watching the token-usage panel. Cost is real but it's the price of not shipping a silent regression.

**"How is 'blocked' decided in the red-team custom probes?"**
> Honestly — the custom-probe detector is a refusal/keyword heuristic, which is a reasonable *gate signal* but can over- or under-count. Phase 1, the Red Team SDK, does the more rigorous service-side evaluation. In production I'd score refusals with a model-based evaluator too. I'm calling that out so you don't take "100% blocked" as gospel.

**"Aren't LLM-as-judge scores non-deterministic?"**
> Somewhat — that's why the judge runs at temperature 0, why thresholds have a WARN band, and why the regression check compares against a baseline with a delta tolerance rather than demanding an exact number. You're detecting *movement*, not asserting an absolute truth.

**"How do you pick thresholds / build the golden dataset?"**
> Start by baselining current production (or a known-good build), set thresholds just under that, and tighten over time. The golden dataset grows from real traffic and incidents — every production surprise becomes a row.

**"How does this compare to LangSmith / Braintrust / Ragas?"**
> Same discipline, different toolbox. Those are great; this happens to be the Azure-native path — `azure-ai-evaluation` + Foundry + App Insights + Actions. The pattern — evaluate in CI, gate on regression, monitor in prod, feed back — is tool-agnostic. Pick what fits your stack.

**"Scores vary between runs — is that a problem?"**
> Expected. The numbers in the README are *representative*, not fixed. That's exactly why we gate on baseline-relative regressions and threshold bands, not on hitting an exact score.

**"Does this slow the pipeline down?"**
> PR eval is seconds-to-a-minute on a small dataset. The heavy full eval and red team run post-deploy / scheduled, off the developer's critical path.

---

## Emergency fallbacks

| Demo | Live command | Fallback file |
|------|-------------|---------------|
| Agent | `make agent-demo` | [fallback/agent_demo_output.txt](../fallback/agent_demo_output.txt) |
| Full eval | `make evaluate` | [fallback/evaluation_results.json](../fallback/evaluation_results.json) |
| **Regression block** | `make demo-regression` | [fallback/regression_comparison_blocked.md](../fallback/regression_comparison_blocked.md) |
| Regression (clean) | `make regression-check` | [fallback/regression_comparison.md](../fallback/regression_comparison.md) |
| Red team | `make redteam` | [fallback/redteam_report.md](../fallback/redteam_report.md) |
| Dashboard | Azure Portal | describe `ce_cm_dashboard.json` |

## Timing checkpoints

| Checkpoint | Target | If behind |
|------------|--------|-----------|
| Finish hook | 7:00 | Cut the story to one sentence; keep the reframe |
| Finish lifecycle + architecture | 15:00 | Skip architecture.md, keep the lifecycle diagram |
| Start full eval | 20:00 | Trim agent demo to 3 min |
| Start regression block | 24:00 | This is the money shot — never skip it |
| Start red team | 32:00 | Show only the report table + one code file |
| Start monitoring | 39:00 | Use the JSON dashboard if the portal is slow |
| Start takeaway | 45:00 | Must hit this — drop the Actions-tab detour if needed |

## If a live demo fails outright

Say it plainly, switch to the recording or the `fallback/` file, keep moving. A calm "here's the run I captured this morning" costs you nothing. Silence and frantic retyping costs you the room.
