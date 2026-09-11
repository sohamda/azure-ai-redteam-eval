# Engineering Continuous Evaluation and Monitoring: Technical Talk Script

Companion to [the technical HTML presentation](../presentation-story.html). This is 50 minutes of content, including live code walkthroughs and demos, followed by Q&A. The script supplies spoken explanations and demonstrations rather than 50 minutes of uninterrupted narration.

Audience: engineers familiar with APIs, CI/CD, and basic LLM application patterns. Assume they want to understand contracts, execution paths, failure modes, and implementation trade-offs. Spend almost no time explaining why monitoring matters in general.

Delivery: live first. Recordings are backups if Azure or the local environment is unavailable. All five existing recordings are accessible from their corresponding slide. The regression fixture is local and does not call Azure; the app, full evaluation, and red-team demos need working Azure dependencies. No application, agent, evaluation, workflow, dataset, or infrastructure changes are part of this presentation revision.

## Presenter Contract

Distinguish three kinds of evidence aloud:

- **Implemented:** visible in the repository code. Show the owning function, not just a comment or filename.
- **Staged:** the regression fixture and the five-row aggregation example. These demonstrate mechanics, not a measured prompt regression.
- **Recommended:** candidate capture, stronger metric validation, statistical calibration, promotion gating, and reviewed incident ingestion. These are production design extensions, not features already implemented here.

The technical story is: a failing quality check is useful only if the response, evaluator, metric adapter, baseline, and release dependency mean what we think they mean. Monitoring has an equivalent chain: producer, span or metric, exporter, query, alert condition, and response owner.

## Run of Show

| Slide | Time | Engineering question | Evidence |
| --- | --- | --- | --- |
| 1 | 00:00-01:00 | What will we implement and inspect? | Three contracts |
| 2 | 01:00-04:00 | Does the checker actually fail? | Local staged regression |
| 3 | 04:00-06:00 | Which paths test the live application? | Three execution paths |
| 4 | 06:00-09:00 | What does the agent chain compute? | Payload and Executor handlers |
| 5 | 09:00-12:00 | What response does CE evaluate? | JSONL and evaluate call |
| 6 | 12:00-15:00 | How do SDK results become policy inputs? | Registry and metric adapter |
| 7 | 15:00-18:00 | What happens when a judge fails? | Custom evaluator and heuristic |
| 8 | 18:00-21:00 | Which scores cause exit 1? | Threshold branches and coverage |
| 9 | 21:00-23:00 | What does the baseline comparison assume? | Relative delta calculation |
| 10 | 23:00-25:00 | Can an average hide a critical failure? | Worked five-row example |
| 11 | 25:00-28:00 | Where does a failed check block execution? | PR/full suites and workflow dependency |
| 12 | 28:00-31:00 | What is the red-team attack surface? | SDK target callback |
| 13 | 31:00-34:00 | Is an unavailable target safe? | Harness errors and report policy |
| 14 | 34:00-37:00 | What do spans and durations actually measure? | ASGI and chat instrumentation |
| 15 | 37:00-39:00 | What does a CE time series represent? | Histogram export and provenance |
| 16 | 39:00-42:00 | How do we investigate one request? | KQL and operation correlation |
| 17 | 42:00-44:00 | Which condition really pages someone? | Bicep alert criteria |
| 18 | 44:00-47:00 | How does an incident become a useful test? | Proposed case artifact |
| 19 | 47:00-50:00 | What should an engineering team take away? | Production checklist |
| 20 | 50:00+ | Questions | Repository and technical discussion |

## Rehearsal and Setup

- Open the deck directly in the browser. Arrow keys navigate; `N` opens presenter cues, `B` opens the current backup recording, and `F` toggles fullscreen. Presenter cues are an on-screen dialog, not a private presenter window: do not leave them projected while speaking.
- Open the companion script on a second device or non-projected screen. Use the slide timings as checkpoints, not as text to read aloud.
- Prepare terminals for the app, evaluation, regression, and red team. Activate the repository virtual environment. Rehearse all commands before the session.
- Pre-run the slow cloud operations and retain completed output. Starting a new run live is optional; waiting for it to finish is not the teaching objective.
- Check which orchestration path is active from startup logs. Do not infer Agent Framework execution from `agents_involved` alone.
- Select one actual request in Application Insights, note its `operation_Id`, and choose a useful time range. Pick a trace you can explain; do not invent an incident to fit the narrative.
- Prepare the exact source locations linked below in editor tabs. Use a large readable editor font and hide unrelated panels.
- Keep secrets, environment files, auth output, and unreviewed production content off screen. Use synthetic queries. Query previews in this app are not automatically redacted.
- Test the five backup videos offline, including sound/muting and fullscreen behavior. The existing videos are walkthroughs, not proof of every technical claim on the revised slides.
- Do not deploy, modify prompts, edit datasets, or change workflows during this talk. Explain proposed changes as designs.

## 1. Opening: Engineering CE and CM

**00:00-01:00. Slide 1.**

> "This is an implementation session. We will follow a response through evaluation, follow a score into a failing process, and inspect where that failure does or does not stop a release. Then we will follow the application's telemetry into queries and alert conditions.
>
> I am using a small Microsoft Agent Framework application, Azure evaluation, OpenTelemetry, and GitHub Actions. The useful part is not the particular vendor combination. It is the contract at every boundary.
>
> I will distinguish what this demo implements from what I would require in production. Let's start with something concrete: a quality regression that returns exit code one."

Skip audience hand-raising and a long problem story. Show the checker immediately.

## 2. Start With the Failing Check

**01:00-04:00. Slide 2.**

Run in the prepared terminal:

```text
make demo-regression
```

Show [the staged comparison](../fallback/regression_comparison_blocked.md) if needed. The expected result is an intentional nonzero exit, not a demo failure.

> "Groundedness moved from 4.7 to 3.2. The delta is minus 1.5, which exceeds the configured regression tolerance. The process returns one. That means a build system can treat quality deterioration as a failure, just as it treats a failing unit test.
>
> These input scores are staged. I have not just changed a prompt and measured a 1.5-point decline. The fixture exercises the actual comparison logic without calling Azure. It proves the failure path, not the validity of the judge or the representativeness of the dataset.
>
> The rest of the talk answers the questions behind this red result: which response was scored, which judge produced the score, what baseline was used, and what depends on this process succeeding?"

**Walkthrough:** point at baseline, current value, delta, and outcome in that order. Show the terminal exit status if the shell exposes it. Do not explain every metric alias yet.

**Backup:** the regression recording is about ten seconds. It is a deterministic mechanics demo and can be presented offline.

**Transition:** "First, separate the three execution paths."

## 3. Architecture: Three Different Paths

**04:00-06:00. Slide 3.**

Sources: [full evaluation runner](../src/continuous_evaluation/run_evaluation.py), [red-team runner](../src/redteam/run_redteam.py), [application](../src/app.py).

> "Stored-response evaluation reads JSONL, asks evaluators to judge the responses in that file, aggregates scores, and applies a policy. The red-team path is different: it generates or loads probes and actually sends requests to the app. The monitoring path observes requests and exports telemetry.
>
> Evaluation jobs also export their scores to Application Insights. That is how the two disciplines share a dashboard. But sharing a dashboard does not make them the same experiment.
>
> If I change the application prompt and only rerun evaluation on unchanged stored responses, the new prompt was not exercised. To test the new candidate end to end, I need a generation step that captures that candidate's responses and context before evaluation. That is an extension to this demo, not something the current runner silently does."

**Point:** use the arrows to identify the input, external calls, and output artifact of each path. CE calls judges; red teaming calls the application target; CM receives telemetry. This distinction is worth more than a full Azure resource inventory.

## 4. Follow the Agent Payload

**06:00-09:00. Slide 4.**

Sources: [orchestrator](../src/agents/orchestrator.py), [planner](../src/agents/planner_agent.py), [retrieval](../src/agents/retrieval_agent.py).

**Demo:** open the warm app at `http://localhost:8000`. Ask: "What are the best practices for deploying AI apps to Azure?" If unavailable, use the app recording and continue with source.

> "The API accepts a query and optional context. AgentPayload carries those fields plus plan, grounded_response, final_response, and the list of agents involved.
>
> WorkflowBuilder creates a fixed planner-to-retrieval-to-safety chain. The planner's handler calls its model, writes the plan into the payload, appends its identifier, and forwards the message. Retrieval builds a prompt from the query, plan, and optional context, then writes grounded_response. The orchestrator extracts the final workflow output.
>
> There are two important scope boundaries. The planner is not dynamically selecting an arbitrary graph here: the chain is fixed. And the retrieval handler does not query a search index. It is a grounding-oriented model call using supplied context.
>
> The orchestrator also has a direct OpenAI fallback selected on certain import failures. That path behaves differently. Before interpreting performance or safety results, verify which implementation ran."

**Code movement:** show `_build_workflow`, `AgentPayload`, and one handler's assignment and `ctx.send_message`. Do not scroll through all three prompts.

**Audience question:** "What would you record to distinguish a retrieval-data change from a model change?" Answer: candidate identity, context or retrieval snapshot, and generation configuration.

## 5. The Evaluation Input Contract

**09:00-12:00. Slide 5.**

Sources: [golden JSONL](../src/continuous_evaluation/datasets/eval_golden.jsonl), [evaluate invocation](../src/continuous_evaluation/run_evaluation.py).

Open row 2. The slide abbreviates its strings; the local file is the source of truth.

> "This row already contains a response. Query is the task; context is the supplied evidence; response is the object being judged; ground_truth is a reference answer. Those are different roles.
>
> Groundedness asks whether a response is supported by the supplied context. Relevance concerns whether it addresses the query. Agreement with a reference answer is yet another question. Adding a ground_truth column does not make every evaluator compare against it.
>
> Now inspect the call: data, evaluators, and evaluation_name. There is no application target callback. The runner is asking the SDK to grade existing answers.
>
> This is useful for demonstrating evaluator behavior and for evaluating captured response snapshots. It is not enough to certify that a newly deployed agent generates better answers. For that, capture fresh candidate responses and the context used to generate them, then evaluate that immutable snapshot."

**Walkthrough exercise:** point at the response field, then remove the editor selection and point at the SDK call. Ask: "Where would the new prompt execute?" There is no such call in this path.

**Nuance:** the reference text itself is not authority about the implementation. Some dataset answers describe idealized release behavior. Use executable code to establish what the demo actually does.

## 6. SDK Results Become Policy Inputs

**12:00-15:00. Slide 6.**

Sources: [registry](../src/continuous_evaluation/evaluators.py), [metric adapter](../src/continuous_evaluation/metrics.py), [full runner](../src/continuous_evaluation/run_evaluation.py).

```text
make evaluate
```

Use an existing completed result if a fresh run is slow. Backup: full evaluation recording.

> "The full registry combines four built-in quality evaluators, custom conciseness, and two safety evaluators. The quality judges receive model configuration; the safety evaluators receive project information and a credential. The judge deployment can be configured separately from the application deployment.
>
> The SDK supplies aggregate metrics. summarize_scores extracts the last component of each dotted name and retains numeric values. For example, groundedness.groundedness becomes groundedness.
>
> That adapter is a small but important boundary. It loses namespace information, does not preserve score direction or scale, and can overwrite two metrics with the same suffix. An unfamiliar result shape returns an empty dictionary.
>
> Follow the remainder of the runner: display scores, export metrics, save results, check thresholds, and exit. A successful SDK call is only one stage. A production gate also needs to know that the right metrics arrived and that enough cases were successfully evaluated."

**Artifact detail:** the saved file contains a structured `scores` dictionary but `raw_results` is `str(results)`. Recommend structured per-case records with judge identity, mode, reasons, and sample counts for production. Do not present the string field as a robust evidence schema.

**Transition:** "Let's look at one judge we own completely."

## 7. Custom Evaluator: Rubric, Callable, Fallback

**15:00-18:00. Slide 7.**

Source: [ConcisenessEvaluator](../src/continuous_evaluation/evaluators.py).

> "The callable accepts response and query as keyword inputs and tolerates extra dataset columns through kwargs. It returns a dictionary whose key becomes a metric name. That is the integration contract.
>
> The rubric defines conciseness as preserving necessary information without redundancy. It explicitly says a short incomplete answer is not concise. The judge request uses JSON output, temperature zero, and a small token budget. The implementation parses the score and clamps it to the one-to-five range.
>
> Now inspect the failure behavior. A judge exception returns None; the callable switches to a word-count heuristic under the same metric name. Fifty words or fewer produces five. An empty response therefore receives five from the heuristic, even though it violates the intended completeness requirement.
>
> This is a useful demonstration fallback, but it is a different measurement method. Production should preserve the mode and decide explicitly whether judge failure means inconclusive, blocking, or a separately calibrated fallback."

**Point at the return value:** the prompt asks for a reason, but the evaluator returns only the numeric score. Discuss the value of retaining reasons for reviewer calibration and diagnosis.

**Audience question:** "Would you allow a release to become green because the judge was down?" Separate operational resilience from validity of the measurement.

**Do not claim:** temperature zero eliminates variance, JSON formatting guarantees semantic correctness, or clamping validates the rubric.

## 8. Exact Threshold Semantics

**18:00-21:00. Slide 8.**

Sources: [threshold functions](../src/continuous_evaluation/thresholds.py), [threshold tests](../tests/unit/test_thresholds.py).

> "The threshold policy has three outcomes, not two. With an illustrative threshold of four and the default warning margin of half a point, four passes, 3.7 warns, and 3.4 fails. The runner exits one only when any result is FAIL. WARN is not a failing process.
>
> There is a second contract before those branches: metric selection. check_all_thresholds removes the gpt_ prefix and checks only names in the known threshold map. That map includes groundedness, coherence, relevance, fluency, and safety. Unknown metrics are skipped. Conciseness does not have an absolute threshold entry here.
>
> This distinction matters: registering an evaluator does not mean every value it returns is governed by a release policy. Content-safety submetrics need explicit semantic mappings, including direction and scale.
>
> Finally, an empty threshold-result list contains no failures. That is logically consistent with any_failures, but insufficient as a production release contract. Validate required metrics and finite values before applying the score thresholds."

**Walkthrough:** show `get_thresholds`, `check_all_thresholds`, the three branches, and `any_failures`. The table's status symbols in formatted output are not the implementation of this policy.

**Check for understanding:** ask whether 3.7 blocks. Then ask what happens when the groundedness key is missing. These expose policy and coverage as separate concepts.

## 9. Regression Semantics and Baseline Identity

**21:00-23:00. Slide 9.**

Sources: [comparison logic](../src/continuous_evaluation/regression_check.py), [regression tests](../tests/unit/test_regression_check.py).

> "Absolute quality asks whether the score clears a policy floor. Regression asks whether it moved too far from a baseline. This checker subtracts baseline from current and marks regression when the delta is strictly below negative tolerance. The default tolerance is 0.3 points.
>
> It iterates current keys. A metric present only in the baseline is skipped; a newly appearing current metric gets a zero baseline. If the baseline file itself is absent, the runner copies current results into it and succeeds without comparison.
>
> Those choices make a small demo easy to bootstrap and accommodate metric-name changes, but they need explicit governance in a release system. Which metrics are mandatory? Who approves a baseline? Are both runs from the same dataset and judge? Are all scores higher-is-better?
>
> A risk rate can improve by decreasing. This generic subtraction policy assumes the opposite. Normalize semantics before applying a shared gate."

**Point:** the tolerance is a score-space threshold, not a statistical significance test. Floating-point values also make exact boundary examples less useful than clear examples such as minus 1.5.

## 10. Calibration: A Worked Failure of Aggregation

**23:00-25:00. Slide 10.**

> "Both of these five-row experiments have a mean of 4.2. The baseline has four common cases scoring four and a critical case scoring five. The candidate improves all four common cases to five but drops the critical case to one. Both totals are twenty-one.
>
> A mean-only regression check sees no movement. Your domain owner sees a serious release risk. That is why I would report per-slice behavior and critical cases, not only one aggregate.
>
> A controlled comparison also freezes the dataset, rubric, judge, and generation configuration. Pair baseline and candidate on the same cases, and distinguish generation variance from judge variance. Repeat runs around a decision boundary and calibrate disagreement against human labels.
>
> These are recommended experiment-design practices. The current checker computes deltas; it does not calculate confidence intervals or evaluate domain slices."

**Arithmetic:** write or point to `21 / 5 = 4.2` for both columns. Label this example constructed, not captured output.

**Budget:** case count times applicable judges times repeats is a useful first estimate of call volume. Token lengths, retries, safety services, and model pricing determine actual cost. Do not promise a fixed price or runtime.

## 11. CI and Release Dependencies

**25:00-28:00. Slide 11.**

Sources: [PR runner](../src/continuous_evaluation/run_pr_evaluation.py), [CI workflow](../.github/workflows/ci.yml), [deployment](../.github/workflows/deploy.yml), [full evaluation workflow](../.github/workflows/evaluate.yml).

> "The PR suite runs after lint and tests, uses five stored rows, registers four quality evaluators, and adds custom conciseness. Notice that get_custom_evaluators is called without model configuration. In the PR suite, conciseness is heuristic. The full suite supplies the model configuration and adds two safety evaluators over ten rows.
>
> A PR gate and a full suite can have different budgets. But their results are not automatically comparable measurements when evaluator modes differ.
>
> Now inspect release wiring. trigger-evaluation has needs: deploy. Full evaluation runs after the application deployment completes. A failure makes the workflow red; it does not undo the deployment. The normal regression step also does not run after an earlier full-evaluation failure, although summary and artifact steps use always.
>
> To protect production promotion, evaluate an isolated candidate and make promotion depend on that result. Promote the exact artifact you tested. To protect merges, configure required checks. These are explicit control-plane decisions, not properties of returning exit one."

**Demo evidence:** a prepared CI run helps explain jobs and artifacts, but a screenshot of a green run is not proof of branch protection or production gating.

**Scope:** do not edit the workflow or trigger a deployment during this walkthrough.

## 12. Red Team Target Contract

**28:00-31:00. Slide 12.**

Source: [SDK setup and callback](../src/redteam/run_redteam.py).

```text
make redteam
```

Prefer a prepared completed run when service latency would consume the section. Backup: red-team recording.

> "Unlike stored-response CE, this callback really sends requests to the application. The SDK invokes it with messages, stream, session_state, and context. Our adapter forwards the final message content as query, passes empty application context, and wraps the result as an assistant message.
>
> That adapter defines the tested surface. It does not forward conversational state or inject a malicious retrieved document. We have selected single-turn Baseline and Jailbreak strategies, so do not describe this as multi-turn coverage.
>
> The SDK configuration uses four risk categories and five objectives each. The custom phase loads ten local probes and produces a separate report with category and severity information. Keep the two result sets separate: their taxonomies and verdict mechanisms differ."

**Show:** the callback signature, HTTP payload, response envelope, and configured strategies. Explain the need to preserve SDK interface contracts as SDK versions change.

**Measurement discipline:** the configured matrix is a plan, not proof every attack and scoring operation completed. Inspect completion and errors before quoting a success rate.

## 13. Harness Integrity and Final Verdict

**31:00-34:00. Slide 13.**

Sources: [probe execution](../src/redteam/attack_strategies.py), [report policy](../src/redteam/report.py), [phase orchestration](../src/redteam/run_redteam.py).

> "The custom harness checks health before probing. Connection failures, timeouts, HTTP errors, and other custom-probe exceptions invalidate the run rather than counting as safe responses. The runner exits two for these target-health failures.
>
> The SDK path has different semantics. The callback converts target-call errors into assistant text. An exception from the SDK phase is logged and the run continues to custom probes. The SDK result is saved, but it is not used to set the final has_critical flag.
>
> The custom detector normalizes apostrophes, recognizes REDACTED, and searches for refusal phrases. SAFE alone is deliberately not a refusal signal. Classification uses the full response; the stored probe response is truncated to five hundred characters.
>
> The report makes high or critical failed probes blocking. A medium-only failure can exist while the overall report remains passing. Read the severity policy before interpreting the headline."

**Audience question:** "Can a response say 'I cannot' and then still leak information?" Yes. A phrase detector can false-pass or false-fail. Production should distinguish pass, fail, and inconclusive, and score whether the protected boundary was actually respected.

**Important:** explain the limitations as harness design choices, not as a claim that the application was successfully attacked during this session.

## 14. Span Ownership and Timing

**34:00-37:00. Slide 14.**

Sources: [request middleware and chat instrumentation](../src/app.py), [telemetry setup](../src/continuous_monitoring/telemetry.py).

> "Telemetry initialization happens in FastAPI lifespan, after worker startup, so exporter threads belong to the serving process. The raw ASGI middleware creates an explicit SERVER span around the request. The chat handler creates a nested chat_request span and records lengths, agent labels, duration, and status.
>
> The code attempts optional httpx instrumentation for outbound dependencies. Agent and model-call spans depend on actual SDK configuration. The local trace_agent decorator exists, but these handlers do not attach it. I will show spans that arrived rather than promise a trace hierarchy based on a helper's existence.
>
> Inspect the duration producer. It measures the entire orchestrator call, then records that same duration under each participating agent label. Grouping this metric by agent does not turn it into that agent's exclusive execution time. For that, instrument the actual boundaries or use verified SDK spans.
>
> There is also a privacy boundary: query.preview can contain the first eighty characters of user input. Truncation is not redaction. Decide what to collect and who may see it."

**Do:** point at `SpanKind.SERVER`, `set_attribute`, the `perf_counter` interval, and the loop that records duration per label.

**Extra detail if asked:** a token counter definition is not a token measurement. The shown chat path does not update that instrument. Similarly, telemetry initialization without a configured exporter is not evidence of Azure ingestion.

## 15. CE Metrics and Provenance

**37:00-39:00. Slide 15.**

Source: [evaluation metric exporter](../src/continuous_monitoring/eval_metrics_exporter.py).

> "Each evaluator score becomes an observation on a histogram named ce.score dot evaluator. The meter is obtained lazily after provider setup, and the exporter requests a flush before a short-lived CLI can exit.
>
> The attributes include evaluator, evaluation name, run ID, and timestamp. In the current runners, run ID is not supplied, so it is empty. These metrics therefore do not automatically link one evaluation result to one application request.
>
> This chart is a history of aggregate evaluation scores, not continuous judging of production answers. For production, keep the metric dimensions bounded and retain detailed candidate, dataset, rubric, case, and judge identity in structured evidence artifacts or controlled events.
>
> Also inspect the exported average. It includes every numeric score. Aliases and mixed-scale safety or binary values can make that average misleading. A quality index needs explicit semantics, not just division by the number of keys."

**Do:** show histogram name, attributes, and caller omission of `run_id`. Do not claim the exported timestamp is an ideal metric dimension; explain its cardinality cost.

## 16. KQL: From Requests to an Operation

**39:00-42:00. Slide 16.**

Source: [workbook queries](../src/continuous_monitoring/dashboards/ce_cm_dashboard.json).

The request-latency query is taken from the workbook. The operation-correlation query is a suggested read-only diagnostic pattern, not a query executed against Azure during preparation of this revision.

> "The latency query reads request records for chat and computes percentiles in five-minute bins. This is materially different from computing percentiles over already-aggregated custom metric values. Know what a row represents before you apply an aggregation.
>
> Choose one observed request and copy its operation ID. The second query brings requests, dependencies, traces, and exceptions for that operation into one time-ordered view. Parent IDs establish relationships. Two records close in time are not necessarily parent and child.
>
> Start with what is present: the request span, its duration and status, then any outbound dependencies and exceptions. If agent-level spans are absent, that is an instrumentation gap, not evidence that the agents took zero time.
>
> These percentiles describe retained telemetry. Sampling and missing data affect what they represent. A batch quality-score trend is a different source and does not automatically identify the slow or incorrect request."

**Live path:** use the prepared Application Insights tab; inspect existing data instead of waiting for newly emitted telemetry. Replace `<operation_Id>` in the suggested query with a real ID and adjust its one-hour range if necessary.

**Offline path:** show the portal recording, then explain each query operator on the slide. No fabricated query output is needed.

**Schema caveat:** the displayed queries use Application Insights names such as `requests` and `operation_Id`. A workspace table context may use `AppRequests`, `TimeGenerated`, and corresponding differently cased fields. Use the correct context; do not assume a query ports unchanged.

## 17. Alert Conditions as Executable Policy

**42:00-44:00. Slide 17.**

Source: [alert criteria](../infra/modules/alerts.bicep).

> "Read the metric name, aggregation, operator, threshold, window, cadence, and action. That is the alert contract. The description is not the contract.
>
> Groundedness uses average below four over fifteen minutes, evaluated every five minutes. The latency rule uses Maximum above five thousand milliseconds, despite a P99 description. Error count above ten in five minutes is a count policy, not an error-rate policy.
>
> There are two more operational checks. Does the exact named metric exist? skipMetricValidation allows deployment without proving the producer emits it. And will anyone receive a notification? Without an action-group ID, the actions list is empty.
>
> Scheduled evaluation scores are sparse. A short alert window does not make them continuously fresh. Add an explicit missing-data or stale-evaluation policy in a production design."

**Comparison:** with the slide's illustrative CI threshold, 3.7 warns without blocking; an average of 3.7 can breach the alert. Separate policies can be valid, but divergence must be intentional and documented.

**Do not claim:** `autoMitigate` rolls back or repairs the app. It concerns alert state, not application remediation.

## 18. Closing the Loop With Reproduction

**44:00-47:00. Slide 18.**

This slide is a proposed schema and operating practice, not implemented automatic ingestion.

> "Suppose we investigate an unsupported guarantee in an answer. We need a reviewed case, not an unfiltered conversation dump. Preserve the task, the necessary redacted context, and the behavior a domain reviewer says was required.
>
> Then record enough identity to reproduce it: candidate revision, dataset version, rubric version, judge deployment, and evaluation mode. Keep this in an evidence artifact with appropriate retention and access, not as unbounded dimensions on a metric.
>
> Run the old candidate to reproduce the failure, then generate a new response from the fixed candidate on the same case and context snapshot. Judge both. Check the relevant slice so the fix does not merely optimize one example at the expense of neighboring behavior.
>
> Notice the key step: regenerate. Re-scoring the same stored response cannot establish that the code fix changed application behavior. The lesson becomes a regression case only when the experiment is reproducible and its label is defensible."

**Audience exercise:** ask what minimum evidence they would need to reproduce a retrieval-related incident a month later. Elicit context snapshot or document version, not just the user question.

**Governance:** review for PII and secrets, assign a label owner, define retention, and preserve unseen holdout cases so the suite does not become the sole optimization target.

## 19. Close: Three Contracts

**47:00-50:00. Slide 19.**

> "We started with a red regression check. Now we know what gives that result meaning.
>
> The measurement contract identifies the candidate, response snapshot, dataset, judge, rubric, metric direction, and coverage. The decision contract defines missing evidence, threshold bands, baseline approval, and which release action actually depends on passing. The observability contract defines what spans and metrics represent, how fresh they must be, and who responds.
>
> You do not need to implement every production extension tomorrow. Choose one release boundary. Make its inputs reproducible, its failure behavior explicit, and its enforcement real. Then choose one production signal and prove that you can follow it back to useful evidence and a reviewed test case.
>
> Continuous Evaluation produces evidence. Continuous Monitoring tests the assumptions behind that evidence. That is the loop."

**Recap interaction:** ask, "Which contract would you test first in your system?" Use a short answer or two to connect the implementation to the audience's work, then leave the repository link visible.

## 20. Technical Q&A

**After 50:00. Slide 20.**

**Why not simply gate on a mean above four?**

Mean aggregation loses case and slice structure. The worked example has an unchanged mean and a critical regression. Add risk-specific policy and validate coverage. A threshold value requires calibration, not just a familiar scale.

**Does this evaluate the deployed agent after every change?**

The full workflow is invoked after deployment, but the current CE runner grades stored JSONL responses. The red-team callback does invoke the app. End-to-end CE would need fresh candidate response and context capture or an appropriately configured evaluation target.

**What makes two baselines comparable?**

At minimum, compatible case set, rubric, judge configuration, metric definitions, and generation context. Preserve candidate and dependency identity. A model deployment alias by itself may not uniquely identify an underlying model version.

**How should I handle judge outages?**

Choose a policy explicitly. Release-blocking inconclusive, controlled retries, or a separately calibrated fallback are different designs. Do not silently interpret absence of measurement as evidence of quality.

**Can the PR and full scores be compared?**

They differ in dataset, evaluator coverage, and the conciseness mode in this repo. Compare like with like, or record those differences rather than treating a dashboard line as one unchanged experiment.

**Is the red-team PASS a security guarantee?**

No. It reflects particular cases, an adapter-limited attack surface, and specific verdict logic. Check scan completeness, target errors, classification reliability, and severity policy. The current final blocking flag is driven by the custom report, not the SDK scan result.

**Where is the per-agent latency?**

The app's labeled duration metric repeats whole-request duration for participating agents. Verify actual agent spans or instrument those boundaries before claiming exclusive per-agent timings. A declared instrument or helper is not proof of emitted telemetry.

**Is the workbook regression view the same as the CI baseline comparison?**

No. The workbook query labeled latest versus previous uses latest and earliest points in its selected time range. The CLI reads an explicit baseline file. Explain the underlying query rather than equating similar labels.

**Does a successful Bicep deployment prove the alert works?**

No. Verify the metric producer, aggregation, data freshness, condition, and notification action. Test the alert response path separately under controlled conditions. This session does not perform a live alert test.

**Where does platform-managed online evaluation fit?**

It can supply sampled production quality signals alongside application telemetry. CI evaluation, promotion policy, online sampling, and incident review are complementary. Choose a tool after defining what evidence and enforcement you need.

## Timing and Failure Recovery

Hard checkpoints: input contract by 12:00; threshold policy by 21:00; release wiring by 28:00; red team complete by 34:00; start close by 47:00. Do not spend the monitoring allocation waiting for a scan.

For **50 minutes including Q&A**, save five minutes as follows: app demo minus one minute, custom evaluator minus one minute, calibration example minus thirty seconds, release wiring minus thirty seconds, red-team demonstration minus one minute, feedback-loop discussion minus one minute. Reach the close at 42:00, finish at 45:00, and reserve five minutes for questions. Keep the semantic boundaries even when skipping editor navigation.

| Demo | Live-first surface | Existing backup | What it does not establish |
| --- | --- | --- | --- |
| Regression | `make demo-regression` | [Recording](../fallback/recordings/make_demo_regression.mp4) | A real prompt change caused those scores |
| App | Warm local `/chat` UI | [Recording](../fallback/recordings/make_agent_demo.mp4) | Which path your current process is using |
| Evaluation | `make evaluate` or completed output | [Recording](../fallback/recordings/make_evaluate.mp4) | Fresh candidate answers were generated |
| Red team | `make redteam` or completed output | [Recording](../fallback/recordings/make_redteam.mp4) | Universal safety or complete coverage |
| Monitoring | Existing request and workbook | [Recording](../fallback/recordings/azure_walkthrough.mp4) | A fabricated incident or newly executed KQL |

When unavailable, say: "The cloud environment is unavailable, so I will use the captured run and show the same contract in code." Stop troubleshooting on stage. The code excerpts, worked examples, and queries carry the technical argument without a deployment.
