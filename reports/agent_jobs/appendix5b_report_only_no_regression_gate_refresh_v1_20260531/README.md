# Appendix 5B Report-Only No-Regression Gate Refresh v1

## Summary

This report refreshes the Appendix 5B PRM-inclusive no-regression gate evidence
for GitHub issue #74 on branch
`safe/appendix5b-report-gate-refresh-v1-20260531`.

The gate passed as a report-local Evaluation artifact. It did not run production
extraction, did not write canonical financial truth, and did not mutate
DB/Qdrant/news/memory stores, source PDFs, parser routing, extraction prompts,
gold labels, Cockpit behavior, or runtime/model/GPU/service config.

Parent tracker: #73.

## Scope

- Task card:
  `docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md`
- Gate output:
  `reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/appendix5b_no_regression_report.json`
- Report directory:
  `reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/`

## Preflight

| Field | Value |
|---|---|
| Agent | Codex |
| Lane | Evaluation |
| Supporting lanes | Financial Truth, Provenance |
| Worktree | `/home/l4nd0/tenn-appendix5b-report-gate-refresh-v1-20260531` |
| Branch | `safe/appendix5b-report-gate-refresh-v1-20260531` |
| Base HEAD | `7ee06fbdad5f954056981769eef3ba25bee86480` |
| Execution mode | `audit_only` |
| Collision risk | LOW |
| Contested surfaces touched | none |

Registry preflight found one live Financial Truth investigation in a different
worktree and one stale Query Orchestration job in the original checkout. The
formal overlap check for this task passed with no issues.

## Gate Result

Command:

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_appendix5b_no_regression_gate.py --output reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/appendix5b_no_regression_report.json
```

Result: PASS.

| Metric | Observed |
|---|---:|
| `canonical_write` | `false` |
| `gate_pass` | `true` |
| `failed_checks` | `[]` |
| `documents_scored` | 7 |
| `document_pass` | 5 |
| `document_fail` | 0 |
| `document_unscored` | 2 |
| `labelled_metric_count` | 13 |
| `labelled_metrics_with_candidate` | 13 |
| `trusted_metric_count` | 13 |
| `match` | 13 |
| `expected_null_respected` | 2 |
| `exact_match_rate` | 1.0 |
| `labelled_metric_coverage` | 1.0 |

## Inputs

- Labels:
  `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/confirmed_labels_prm_included.json`
- Candidate artifacts:
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_q4_fy2025_appendix5b.rerun_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/eqr_q4_fy2026_appendix5b.rerun_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_q_2025-09-30.rerun_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/gre_asx_june2025_alt.rerun_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/pek_asx_july2025_probe.rerun_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/baseline_artifacts/tenx_artifact.json`
  - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_artifact.json`

## Validation

| Check | Result |
|---|---|
| Task-card validation | PASS |
| Registry list-active inspected | PASS |
| Registry overlap check | PASS |
| Registry claim | PASS |
| Appendix 5B no-regression gate | PASS |
| Gate JSON parse | PASS |
| Status / validation / code-review JSON parse | PASS |
| Focused Appendix 5B pytest | PASS: 20 passed |
| `git diff --check` | PASS |
| `git diff --cached --check` | PASS |
| Task-card `check-diff` | PASS |
| Registry release | PASS |
| Code-reviewer pass | PASS: no findings |
| `canonical_write=false` proof | PASS |
| Product/runtime/financial-truth mutation check | PASS |

## Closeout Decision

Issue #74 satisfies the report-only completion gate once this task card and
report bundle are committed and linked to #74 and #73.

Issue #73 remains open because it is the broader ASX evidence-bound extraction
redesign parent tracker.

## DATA_MISSING

- `graphify-out/wiki/index.md` and `graphify-out/GRAPH_REPORT.md` are absent in
  this checkout, so graphify community/god-node evidence could not be included.
