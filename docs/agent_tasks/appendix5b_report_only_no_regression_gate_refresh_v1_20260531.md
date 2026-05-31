---
job_id: appendix5b_report_only_no_regression_gate_refresh_v1_20260531
title: Appendix 5B Report-Only No-Regression Gate Refresh v1
owner: Codex
lane: Evaluation
primary_lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
mutation_mode: audit_only
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531
allowed_files:
  - docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/README.md
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/status.json
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/validation.json
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/appendix5b_no_regression_report.json
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/diff-check.json
  - reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/code_review.json
allow_audit_code_changes: true
---

# Appendix 5B Report-Only No-Regression Gate Refresh v1

Refresh the Appendix 5B PRM-inclusive no-regression gate evidence for GitHub
issue #74 on the current branch without changing production extraction behavior
or canonical financial truth.

## Scope

- Run the existing report-local Appendix 5B no-regression gate into this task's
  bounded report directory.
- Preserve the exact gate artifact and a concise status report.
- Link the result to issue #74 and parent tracker #73 if validation passes.

## Required Command Shape

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_appendix5b_no_regression_gate.py --output reports/agent_jobs/appendix5b_report_only_no_regression_gate_refresh_v1_20260531/appendix5b_no_regression_report.json
```

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md`
- Appendix 5B no-regression gate command above
- JSON parsing for report artifacts
- `git diff --cached --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/appendix5b_report_only_no_regression_gate_refresh_v1_20260531.md`
- `python3 scripts/agent_job_registry.py release appendix5b_report_only_no_regression_gate_refresh_v1_20260531`

## Acceptance Criteria

- `canonical_write=false`
- `gate_pass=true`
- `failed_checks=[]`
- Documents scored, document pass/fail/unscored counts, labelled metric count,
  trusted metric count, exact-match rate, labelled-metric coverage, and
  expected-null handling are all present in the gate report.
- Task-card validation, overlap check, artifact JSON parsing, whitespace check,
  and task-card diff check pass.
- No forbidden surface changes are required.

## Allowed GitHub Closeout

If the report artifact is committed and all validation passes, Codex may:

- comment on issue #74 with a closeout summary;
- close issue #74 as completed with evidence;
- comment on parent issue #73 with the linked child result.

No labels, milestones, PR creation, branch cleanup, merge, rebase, reset, stash,
prune, delete, cherry-pick, or production data mutation is authorized by this
task card.

## Hard Boundaries

Do not change:

- production parser routing;
- Docling configuration;
- extraction prompts;
- canonical financial truth writes;
- source PDFs;
- DB/Qdrant/news/memory stores;
- model/runtime/GPU/service config;
- gold labels;
- Cockpit product or runtime behavior;
- unrelated dirty files.

Do not promote, relabel, or broaden Appendix 5B truth. This task refreshes a
report-local no-regression gate only.

## System Contract Compliance

Target system layer: Evaluation/reporting artifact only. The gate reads committed
report-local labels and candidate artifacts, and writes a report-local JSON file.

Relevant contract rules:

- Backend remains the sole authority for production data and retrieval.
- The mandatory pipeline order is preserved; this task does not run ingestion,
  extraction, storage, retrieval, analysis, or client mutation.
- Appendix 5B capex derivation remains limited to the documented exception.
- No silent fallback, substitution, canonical write, or data-store mutation is
  introduced.

GPU guard: not required. This task does not spawn, restart, or depend on
llama-server.

## Closeout Gate

Issue #74 can close only if the committed report-local artifact proves the
Appendix 5B gate still passes on this checkout and the result is linked back to
parent issue #73.
