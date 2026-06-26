# State

## Evidence

- Current worktree: `/home/l4nd0/tenn-issue280-direct-startup-diagnostics-current-base-v3-20260627`
- Branch: `safe/issue280-direct-startup-diagnostics-current-base-v3-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@b58ec5a047f6b6bd42c4d567c299e6e9601c5225`
- Guard result: `VALID_TASK_WORKTREE`, `stop_reimplementation=false`
- Registry overlap: clean
- Registry claim: active for `direct_startup_runtime_diagnostics_current_base_v3_20260627`
- Ledger: live and committed sources validated; claim and implementation-start entries appended
- Duplicate-work classification: `SUPERSEDE` for stale dirty v1 worktree, no open PR found for #280

## Docs Impact

- `docs_impact`: `DOCS_NOT_REQUIRED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`,
  `docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md`,
  `docs/entrypoints.md`
- `docs_changed`: none
- `docs_followup`: none
- `reason`: the change adds startup log diagnostics and a local-entrypoint
  marker; behavior and operator entrypoints remain unchanged.

## Model And Worker Routing

- `task_tier`: `medium`
- `recommended_model`: `standard coding model`
- `actual_model`: `Codex GPT-5`
- `why_this_model`: focused backend/script diagnostics with unit tests
- `worker_model_allowed`: `false`
- `worker_decision_limit`: no workers used; scope was narrow and source-local
- `escalation_needed`: `false`

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Backend startup logs report entrypoint, task mode, DB URL class, feature flags, and direct-startup warning when production-like defaults are active. |
| live output location | Backend process logs from future startup; no backend process was started in this task. |
| pre-run max timestamp or count | `DATA_MISSING` - no live startup log baseline captured because service starts were out of scope. |
| post-run max timestamp or count | `DATA_MISSING` - no live startup was executed. |
| rows/files inserted or updated after run start | Zero live runtime rows/files. Source and test files only. |
| readiness/gate status | Code diagnostics validation passed; live runtime gate not exercised. |
| exact command/query used | `uv run --with pytest pytest -q financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | Live backend startup/log output was intentionally not run; runtime output freshness remains unproven. |

- result: `PARTIAL`

## Closeout Status

`DONE_WITH_RISK`: code and focused tests are ready for PR review. Runtime
functionality is not proven beyond deterministic diagnostics tests.
