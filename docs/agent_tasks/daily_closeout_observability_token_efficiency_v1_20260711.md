---
job_id: daily_closeout_observability_token_efficiency_v1_20260711
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md
  - scripts/codex_automation_observability.py
  - scripts/codex_automation_runner.py
  - scripts/test_codex_automation_observability.py
  - scripts/test_codex_automation_runner.py
  - docs/dev/automation_index.md
  - docs/dev/schemas/codex_daily_closeout_output_v1.schema.json
  - docs/dev/schemas/codex_automation_evidence_v1.schema.json
  - docs/dev/schemas/codex_automation_run_v1.schema.json
  - docs/dev/schemas/codex_automation_review_v1.schema.json
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/README.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/STATE.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/DECISIONS.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/VALIDATION.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/CODE_REVIEW.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/APPROVAL_MANIFEST.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/HANDOFF.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/NEXT_GOAL.md
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/ledger_entry.json
  - reports/agent_jobs/daily_closeout_observability_token_efficiency_v1_20260711/diff-check.json
---

# Daily Closeout Observability And Token Efficiency V1

## Approval

USER_APPROVED: Orlando invoked the exact Shot 2 `/goal` from the approved Shot
1 packet. Approval covers repo-side implementation and focused validation only.

## Publication Group P Override - 2026-07-11

USER_APPROVED: Orlando invoked the exact Publication Group P `/goal` after the
repo-only handoff. This current instruction supersedes the earlier publication
restriction only for staging the exact allowlist, force-adding the exact report
bundle, creating one coherent commit, pushing the existing task branch, and
opening a draft PR.

Still not approved: merge, rebase, execution-worktree retarget or deployment,
systemd action, live model or scheduled run, host-global automation output,
retention deletion, GitHub issue mutation, or runtime/data/extraction/model
mutation.

## Source Packet

- Task card:
  `docs/agent_tasks/daily_closeout_observability_token_efficiency_shot1_v1_20260711.md`
- Report packet:
  `reports/agent_jobs/daily_closeout_observability_token_efficiency_shot1_v1_20260711/`
- Approved manifest group: `Group B - Shot 2 Repo Implementation`

The source packet lives in the preserved Shot 1 worktree and was read before
this task card was created.

## Objective

Implement a daily-closeout-only observability tracer bullet that joins bounded
native evidence, normalized fact changes, deterministic usefulness, a native
zero-model fast path, explicit model gating, structured model output, run
provenance, usage accounting, human reporting, immutable reviews, and
seven-run aggregation.

## Scope

- Add four versioned JSON schemas for model output, evidence, run, and review
  records.
- Add one standard-library observability module with a read-only summary CLI
  and explicit review-write CLI.
- Integrate only the `daily-closeout` runner path and native automation-health
  summary.
- Preserve current behavior for all other Codex automation jobs.
- Add focused unit tests and a fake-Codex end-to-end runner test using temporary
  output roots.
- Update the automation index with lifecycle, artifacts, operator commands,
  proof gates, and safety boundaries.
- Produce a report-local handoff and separate approval groups for publication,
  deployment, and scheduled proof.

task scope: `control_plane_only`

## Hard Boundaries

- No writes under `/home/l4nd0/.codex/automations/tenn` during validation.
- No live Codex child/model invocation. Tests must use a fake child.
- No execution-worktree mutation or systemd command that changes state.
- Publication exception: one exact allowlisted commit, existing-branch push,
  and draft PR are approved. No merge, rebase, reset, stash, clean, pruning,
  worktree deletion, branch deletion, force push, or other GitHub write.
- No runtime, DB, Qdrant, Redis, news, memory, source-PDF, gold-label,
  extraction, canonical truth, model/GPU config, secret, or production-data
  mutation.
- No retention deletion, database, UI, automatic retry, larger-model fallback,
  rollback, service change, or instrumentation rollout to other jobs.
- No path outside `allowed_files`.
- No live Task Ledger or registry mutation; preserve the intended transition
  in the report bundle.

## Required Validation

- `python3 scripts/tenn_dev_status.py`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md`
- `python3 -m json.tool docs/dev/schemas/codex_daily_closeout_output_v1.schema.json`
- `python3 -m json.tool docs/dev/schemas/codex_automation_evidence_v1.schema.json`
- `python3 -m json.tool docs/dev/schemas/codex_automation_run_v1.schema.json`
- `python3 -m json.tool docs/dev/schemas/codex_automation_review_v1.schema.json`
- `python3 -m unittest scripts/test_codex_automation_observability.py scripts/test_codex_automation_runner.py`
- `python3 scripts/codex_automation_runner.py list`
- `python3 scripts/codex_automation_observability.py --help`
- Temporary-root daily-closeout dry-run; no live output root and no real Codex
  process.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/daily_closeout_observability_token_efficiency_v1_20260711.md`
- `git diff --check`
- Final code/diff review and `git status --short --untracked-files=all`.

## Definition Of Done

- All scoped behavior has focused tests and preserves non-daily jobs.
- No validation command writes the live automation root or invokes a live
  model.
- Documentation matches the implemented artifact and CLI contract.
- Task-card, schema, unit, diff, artifact, and closeout validation pass.
- Report records docs impact, model/worker routing, ledger/registry state,
  functionality proof boundary, ignored artifacts, unsafe actions avoided,
  and exact next prompt.
- Closeout is `DONE_WITH_RISK` because live scheduled functionality remains
  separately approval-gated and unproven.
