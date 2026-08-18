---
job_id: extraction_whc_openability_exact_replay_v1_20260611
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_openability_exact_replay_v1_20260611.md
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/README.md
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/status.json
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/live_git_status.json
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/replay_result.json
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/validation.json
  - reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611/diff-check.json
approval_required: false
allow_unapproved_safe_extension: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_openability_exact_replay_v1_20260611
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# WHC Openability Exact Replay

## Objective

Run one exact local replay for WHC document
`9640d9f1-a45b-492d-8df5-9bad0f46431c` with
`openability_selected_tables=True` to determine whether the opt-in bridge can
produce canonical metrics through existing Pass 2, Pass 3a, Pass 4, and
validation gates.

This task is report-only. It must not change code. If the replay exposes a
repair need, create or recommend a separate bounded task card.

## Scope

- Exact ticker: WHC
- Exact document id: `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- Exact source PDF:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf`
- Parser backend: `pymupdf`
- Openability pages: 57, 58, 60, 61
- Cache/data root: temporary report-local directory only, removed or recorded
  after replay.

## Allowed Run

- One local `run_multipass_extraction(...)` call for the exact PDF above.
- `skip_narrative=True`.
- `openability_selected_tables=True`.
- `openability_pages=[57, 58, 60, 61]`.
- Record payload/status/error/debug capture into report JSON.

## Hard Stops

- Do not change code in this task.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker-universe extraction, service routes, or production DB writes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, production data,
  prompts, gold labels, schemas, runtime state, model config, or GPU config.
- Do not use PR #318 as a patch source.
- Stop report-only if local LLM/test runtime is unavailable.

## Validation

- Task card validate.
- Registry `list-active --read-only`.
- Exact replay command exit status.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface audit.

## Final Report Requirements

Report branch/HEAD/worktree, PR #340 status, registry state, replay command,
status/error, accepted non-null metrics if any, validation gates, debug capture,
scorecard gain if measurable, `DATA_MISSING`, forbidden actions not run, and
the next recommended task.
