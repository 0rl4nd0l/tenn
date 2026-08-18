# Registry Read-only No-lock List-active v1

Issue: #80

Mode: safe_extension

Primary lane: Repo Hygiene

Supporting lanes: Reporting, Evaluation

## Summary

Implemented a minimal `list-active --read-only` mode in
`scripts/agent_job_registry.py`. The read-only path resolves the same registry
location and loads active job records, but it does not enter `RegistryLock`, does
not create the registry root, does not create `.lock`, and does not write active
records, heartbeats, releases, prune metadata, or timestamps.

Existing `list-active` behavior remains lock-backed and backward compatible.
Existing claim/release/write behavior is unchanged.

## Branch / HEAD

- Source checkout branch before isolation:
  `migration/clean-runtime-baseline-reconstruct-v1`
- Source checkout HEAD before isolation:
  `326b60db92bf286344c2bb90ed504ab5378a94a2`
- Implementation worktree:
  `/home/l4nd0/tenn-registry-readonly-no-lock-v1-20260525`
- Implementation branch:
  `safe/registry-readonly-no-lock-list-active-v1-20260525`
- Implementation base HEAD:
  `326b60db92bf286344c2bb90ed504ab5378a94a2`
- Commit hash:
  `DATA_MISSING`: this report is written before the commit that will contain it.

## Changed files

- `scripts/agent_job_registry.py`
- `scripts/test_agent_job_registry.py`
- `docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md`
- `reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/README.md`
- `reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/status.json`
- `reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/validation.json`
- `reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/diff-check.json`

## Validation summary

- PASS: `python3 scripts/agent_job_registry.py --help`
- PASS: `python3 scripts/agent_job_registry.py list-active --help`
- PASS: `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- PASS: live read-only command returned `read_only: true` and
  `lock_acquired: false`.
- PASS: shared registry file content/mtime snapshot unchanged before/after the
  live read-only command.
- PASS: `.lock` did not exist after the live read-only command.
- PASS: `uv run --with pytest --with PyYAML pytest -q scripts/test_agent_job_registry.py`
  reported `16 passed, 1 warning`.
- PASS: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md`
- PASS: `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md --repo-root .`
- PASS: `git diff --check`

## Active jobs and overlap

At validation time the shared registry had one unrelated active job:

- `strict_local_news_context_claim_verified_route_v1_20260526`
- Lane: `Query Orchestration`
- Worktree: `/home/l4nd0/tenn-strict-local-news-context-claim-verified-route-v1-20260526`

The task-card overlap check passed because the active job does not share this
task's lane, output directory, or allowed files.

## DATA_MISSING

- The project-local Python environment does not expose `pytest` through
  `/usr/bin/python3`; validation used ephemeral `uv run --with pytest --with
  PyYAML` instead.
- The final commit hash is `DATA_MISSING` in this report because the report is
  part of the commit payload.
- GitHub Project field backfill for #80 remains `DATA_MISSING`; this task only
  updates the issue thread/state after validation.

## Forbidden surface attestation

No product/backend/frontend/runtime code was changed. No DB, Qdrant, news,
memory, canonical financial truth, parser routing, extraction prompts, gold
labels, model/runtime/GPU/service config, branch cleanup, merge, rebase, reset,
stash, prune, or delete was performed.
