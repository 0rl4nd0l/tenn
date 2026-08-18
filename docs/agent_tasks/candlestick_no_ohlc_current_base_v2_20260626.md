---
job_id: candlestick_no_ohlc_current_base_v2_20260626
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626
mutation_mode: safe_extension
production_data_access: false
issue: 275
allowed_files:
  - docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_action_execute.py
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/README.md
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/STATE.md
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/VALIDATION.md
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/status.json
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/diff-check.json
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/PR_BODY.md
  - reports/agent_jobs/candlestick_no_ohlc_current_base_v2_20260626/REVIEW.md
github_writes_allowed:
  - draft PR after local validation
  - issue comment after merge containment
  - issue close only after canonical merge containment
---

# Candlestick No-OHLC Current-Base Fix

## Objective

Fix issue #275 from current canonical by making a `show_candlestick` action
with no backend OHLC history return a clear no-data / `DATA_MISSING` state
instead of a raw action failure.

## Scope

- Port the prior validated local fix from the stale
  `safe/issue275-candlestick-no-ohlc-v1-20260626` branch as reference-only.
- Repair only the bounded action response path in
  `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Add or preserve focused backend action-execute coverage in
  `financial-engine_v2/backend/tests/test_cockpit_api_action_execute.py`.
- Record validation, PR, and issue closeout evidence in the report artifacts.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory, source PDF, extraction prompt, parser,
  gold-label, model/GPU, or production-data mutation.
- No hidden OHLC fabrication, synthetic candles, or external market-data fetch.
- No treating missing OHLC as verified market evidence.
- No unrelated Cockpit suggested-action work; #122 and #40 stay separate.
- No frontend edits unless backend-only validation proves insufficient.
- No merge, rebase, reset, stash, branch deletion, or cleanup.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue275-candlestick-no-ohlc-current-base-v2-20260626 --topic "issue 275 candlestick no OHLC current base v2" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap candlestick_no_ohlc_current_base_v2_20260626 --task-card docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim candlestick_no_ohlc_current_base_v2_20260626 --task-card docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md --repo-root .`
- Focused backend action-execute tests for no-OHLC and successful chart paths.
- `uv run --with ruff ruff check` on touched Python files.
- `uv run --with ruff ruff format --check` on touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/candlestick_no_ohlc_current_base_v2_20260626.md --repo-root .`

## Definition Of Done

- No-OHLC candlestick action returns a user-facing no-data / `DATA_MISSING`
  state rather than a raw `SYSTEM` action failure.
- The response explains that no chart can be rendered from current OHLC
  evidence for the ticker.
- Existing successful chart rendering still returns a renderable chart payload.
- No fabricated candles, fallback market data, external fetching, or
  frontend-only evidence relabeling is introduced.
- Local validation and GitHub checks pass.
- PR is merged into `migration/clean-runtime-baseline-reconstruct-v1` and merge
  commit containment is verified before issue #275 is closed.
