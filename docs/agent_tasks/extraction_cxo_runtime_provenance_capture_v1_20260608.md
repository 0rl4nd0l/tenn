---
job_id: extraction_cxo_runtime_provenance_capture_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_cxo_runtime_provenance_capture_v1_20260608.md
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/README.md
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/capture_runtime_provenance.py
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/runtime_provenance_capture.json
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/common_metric_source_scale_trace.json
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/status.json
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/validation.json
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/task_card_validate.log
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/capture_runtime_provenance.log
  - reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608/logs/validation.log
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_cxo_runtime_provenance_capture_v1_20260608
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: false
---

# CXO Runtime Provenance Capture

## Objective

Build an exact-doc, no-write runtime provenance capture for CXO plus one
additional clean scale-known control from the fixed scale-table harness. Capture
row refs, selected table/page, row/cell text, table-local scale, same-page
scale, document-level scale, `metric_source_scales`, `metric_scale_sources`,
and `_common_metric_source_scale` input/output where current no-write artifacts
or safe exact-doc runtime hooks expose them.

## Scope

Mode: REPORT_LOCAL / NO-WRITE capture first. Do not implement any production
repair unless two clean exact-doc cases prove the same source-bound root cause.

Exact target documents:

- CXO `36e172ec-2650-4a9f-9ef0-a4366a3b8d31`
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`, unless live harness evidence
  proves a cleaner scale-known control.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, full ticker-universe extraction, or
  broad production runtime routes.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, model/GPU/service config, parser cache,
  or production data.
- Do not start services.
- Do not use a runtime/pass3a route if it would write forbidden surfaces.
- Do not create, edit, label, comment on, close, or reopen GitHub issues or PRs.
- Do not merge, rebase, reset, stash, clean, delete branches, or modify the
  dirty shared checkout.

## Required Evidence

- Live worktree preflight: path, branch, HEAD, origin, dirty state.
- Safe registry read-only output.
- Fixed harness entries for CXO and the chosen second control.
- Count-24 persisted summaries for the exact docs, used as prior accepted
  output evidence only.
- Current `multipass_extraction.py` debug capture and
  `_common_metric_source_scale` signatures before invoking any helper.
- Existing parser cache only; if unavailable, mark `DATA_MISSING`.

## Required Output

- `runtime_provenance_capture.json`
- `common_metric_source_scale_trace.json`
- `status.json`
- `validation.json`
- Report `README.md` with commands, exit statuses, unsafe actions avoided,
  files touched, files intentionally not touched, `DATA_MISSING`, validation,
  exact docs used, whether the two cases shared a root cause, whether any
  production repair was implemented, blockers, and next recommended prompt.
