---
job_id: cockpit_start_config_portable_engine_root_v1_20260715
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_start_config_portable_engine_root_v1_20260715.md
  - scripts/start_config.env
  - scripts/test_cockpit_launcher_helpers.py
  - reports/agent_jobs/cockpit_start_config_portable_engine_root_v1_20260715/STATE.md
  - reports/agent_jobs/cockpit_start_config_portable_engine_root_v1_20260715/DECISIONS.md
  - reports/agent_jobs/cockpit_start_config_portable_engine_root_v1_20260715/VALIDATION.md
  - reports/agent_jobs/cockpit_start_config_portable_engine_root_v1_20260715/RUN_OUTCOME.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_start_config_portable_engine_root_v1_20260715
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
---

# Cockpit start config portable engine root

## Objective

Replace the deleted-worktree `ENGINE_ROOT` default with the current checkout's
`financial-engine_v2` directory, add one focused launcher-config regression
test, and retry the owner-requested `cockpit start new` runtime action.

## Approval

USER_APPROVED: On 2026-07-15 Orlando approved a one-line portable config fix in
a fresh canonical task worktree followed by focused validation and a Cockpit
retry. This approval includes the documented full-stack runtime side effects of
`cockpit start new`. It does not authorize commit, push, GitHub mutation,
registry mutation, database/data cleanup, service-config expansion, or
unrelated edits.

## Allowed implementation

- Change only the `ENGINE_ROOT` assignment in `scripts/start_config.env`.
- Add one focused regression assertion to the existing launcher-helper tests.
- Write only the allowlisted evidence files.
- Run `cockpit start new` and verify the UI and backend health endpoints.

## Hard stops

- Any additional launcher, Docker Compose, model/GPU, secret, database, Qdrant,
  Redis, news, memory, extraction, or production-data change.
- Any overlapping active job, stale canonical base, or unexpected worktree dirt.
- Any need to commit, push, create a PR, mutate GitHub, or mutate the registry.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_start_config_portable_engine_root_v1_20260715.md`
- Portable Git guard preflight with the task card.
- Focused RED/GREEN check for the portable `ENGINE_ROOT` contract.
- `python3 -m pytest -q scripts/test_cockpit_launcher_helpers.py`
- `git diff --check`
- Task-card `check-diff`.
- Runtime functionality proof for `http://127.0.0.1:8081` and
  `http://127.0.0.1:8000/api/health`.
