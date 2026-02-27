# Regression Comparison — Fallback Demo Output

> Generated: 2026-02-26T09:55:00Z

## Score Comparison: Baseline vs. Current

| Metric         | Baseline | Current | Delta  | Status |
|----------------|----------|---------|--------|--------|
| Groundedness   | 5.00     | 4.70    | -0.30  | ✅ PASS |
| Coherence      | 4.00     | 4.00    | +0.00  | ✅ PASS |
| Relevance      | 4.20     | 4.60    | +0.40  | ✅ PASS |
| Fluency        | 4.00     | 4.10    | +0.10  | ✅ PASS |
| Conciseness    | 4.90     | 4.95    | +0.05  | ✅ PASS |

## Summary

- **Regressions detected**: 0 (threshold: delta > 0.3)
- **Improvements**: Relevance (+0.40), Fluency (+0.10), Conciseness (+0.05)
- **Unchanged**: Coherence (4.00)
- **Slight decrease**: Groundedness (-0.30, within threshold)
- **Overall verdict**: ✅ **No regressions** — safe to deploy

---

*Regression threshold: 0.3 — any metric dropping more than 0.3 from baseline triggers a failure.*
*Baseline from: evaluation_baseline.json (5 rows). Current from: evaluation_results.json (10 rows).*
