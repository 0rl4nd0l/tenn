---
job_id: extraction_cxo_nsr_pass3a_debug_replay_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608.md
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/README.md
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.py
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/pass3a_debug_replay.json
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/common_metric_source_scale_trace.json
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/status.json
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/validation.json
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/task_card_validate.log
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/cache_support_probe.log
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/pass3a_debug_replay.log
  - reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608/logs/validation.log
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_cxo_nsr_pass3a_debug_replay_v1_20260608
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: false
---

# CXO/NSR Pass3a Debug Replay

## Objective

Run an approval-gated exact-doc pass3a debug replay for CXO and NSR only,
allowing parser-cache writes only to an isolated disposable cache directory if
the code supports it. Capture actual pass3a outputs, row refs,
`metric_source_scales`, `metric_scale_sources`, selected table/page, and
`_common_metric_source_scale` input/output.

## Scope

Mode: REPORT_LOCAL. The user has approved only this exact-doc replay and only
with isolated disposable parser-cache writes if supported by current code.

Exact target documents:

- CXO `36e172ec-2650-4a9f-9ef0-a4366a3b8d31`
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run random samples.
- Do not run broad extraction, backfill, full ticker-universe extraction, or
  broad production runtime routes.
- Do not mutate DB, Qdrant, Redis, news stores, memory, source PDFs, prompts,
  gold labels, runtime config, schemas, model/GPU/service config, normal parser
  cache, or production data.
- Do not start services.
- Do not create, edit, label, comment on, close, or reopen GitHub issues or PRs.
- Do not merge, rebase, reset, stash, clean, delete branches, or modify the
  dirty shared checkout.
- If isolated disposable parser-cache replay is not supported by current code,
  stop at `WAITING_ON_USER` or `DONE_WITH_RISK` with exact evidence rather than
  writing the normal parser cache.
- Do not implement production repair unless both exact documents prove the same
  source-bound production root cause.

## Required Evidence

- Live worktree preflight: path, branch, HEAD, origin, dirty state.
- Safe registry read-only output.
- Task card validation before implementation-capable edits.
- Current evidence that parser-cache writes can be redirected to an isolated
  disposable cache directory, or exact evidence that they cannot.
- Exact-doc pass3a replay artifacts for CXO and NSR only if the cache boundary
  is safe.
- Before/after checks proving normal parser-cache paths, source PDFs, DB,
  Qdrant, Redis, news stores, prompts, gold labels, and runtime config were not
  touched by this report-local job.

## Required Output

- `pass3a_debug_replay.json`
- `common_metric_source_scale_trace.json`
- `status.json`
- `validation.json`
- Report `README.md` with commands, exit statuses, unsafe actions avoided,
  files touched, files intentionally not touched, `DATA_MISSING`, validation,
  exact docs used, isolated cache usage, pass3a field capture status, whether
  the two cases shared a root cause, whether any production repair was
  implemented, blockers, and next recommended prompt.
