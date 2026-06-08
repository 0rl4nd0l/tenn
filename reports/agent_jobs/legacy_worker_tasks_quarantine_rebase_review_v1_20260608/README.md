# Legacy Worker Task Quarantine Rebase Review

## Summary

Replays the parked #267 legacy worker quarantine work onto current `origin/migration/clean-runtime-baseline-reconstruct-v1` for PR review through #327.

## Preflight

- Source issue: #267
- Branch-review issue: #327
- Source parked branch: `safe/legacy-worker-tasks-quarantine-v1-20260602`
- Source parked commit: `5a9f371407d3fd6e6538dd59429024175954ad4c`
- New branch: `safe/legacy-worker-tasks-quarantine-review-v1-20260608`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD at worktree creation: `ca65fe244048464b473a7789e1a66aff864de577`
- Replay commit: the commit containing this report on `safe/legacy-worker-tasks-quarantine-review-v1-20260608`
- Worktree: `/home/l4nd0/tenn-legacy-worker-tasks-quarantine-review-v1-20260608`

## Result

Replayed the parked legacy worker quarantine code/test changes onto current base `ca65fe244048464b473a7789e1a66aff864de577`.

Changed surfaces:

- `financial-engine_v2/worker/app/tasks.py`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py`
- `docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md`
- `reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/*`

Boundary compliance:

- No production DB/Qdrant/news/memory mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No live worker start, stop, restart, or task execution.
- No unrelated dirty work from `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` touched.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md` - PASS
- `python3 scripts/agent_job_registry.py list-active --read-only` - PASS, `active_jobs=[]`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md` - PASS
- `python3 -m py_compile financial-engine_v2/worker/app/tasks.py financial-engine_v2/backend/tests/test_architecture_invariants.py` - PASS
- Static fail-closed import probe - PASS
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_architecture_invariants.py -q` - PASS, 11 passed
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/test_celery_task_registration_smoke.py` - PASS, 3 tests OK
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/worker/app/tasks.py financial-engine_v2/backend/tests/test_architecture_invariants.py` - PASS
- `python3 -m json.tool reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/status.json` - PASS
- `python3 -m json.tool reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/validation.json` - PASS
- `python3 -m json.tool reports/agent_jobs/legacy_worker_tasks_quarantine_rebase_review_v1_20260608/code_review.md` - PASS
- `git diff --check && git diff --cached --check` - PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md --no-write-report` - PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/legacy_worker_tasks_quarantine_rebase_review_v1_20260608.md` - PASS, wrote `diff-check.json`

## GitHub

Pending PR creation at the time this report was committed.
