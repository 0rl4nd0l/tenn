# A2M News Projection Canonical Integration and Status Reporting Controller

Generated: 2026-05-25T14:03:15+10:00

## Result

Integration succeeded. The two parked commits were cherry-picked into canonical
`/home/l4nd0/tenn` with provenance preserved by `-x`:

- `a94acba7` from `2d1e810bcb978cc062d5de81d2c6b6198a76b8a4`
- `226dfc4a` from `b47d0497d24ec8dce5bf3e75c314b5c3a758ef7c`

The status-reporting child ran as a report/status artifact extension only. No
source, route, test, DB, Qdrant, runtime, service, Docker, env, model, GPU, or
UI implementation files were changed.

## Confirmed

- Canonical started on branch
  `migration/clean-runtime-baseline-reconstruct-v1` at
  `6eb30d3f098849c501d2239a188374bd822d6000`.
- Before integration, canonical had only the two known foreign untracked task
  cards:
  - `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
  - `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`
- The parked worktree
  `/home/l4nd0/tenn-a2m-news-projection-controller-v1-20260525` was clean at
  `b47d0497d24ec8dce5bf3e75c314b5c3a758ef7c`.
- The two parked commits touched only A2M task cards and report artifacts.
- Canonical had no tracked or untracked files at those parked A2M artifact
  paths before cherry-pick.
- The integrated read-only smoke shows A2M is user-visible through
  Qdrant-backed backend and Cockpit `/rag/query`.
- Canonical NVMe SQLite projection files are still absent.
- Legacy `/mnt/sdb2` SQLite evidence is provenance only, not a current canonical
  consumer.
- Cockpit status visibility is incomplete: the integrated smoke recorded
  `/api/cockpit/news/status` and `/api/cockpit/status` as 404.
- The two foreign task cards were not cleaned, moved, staged, committed, or
  overwritten.

## Inferred

- The honest route-health status is split, not "A2M missing":
  `qdrant_retrieval=ok`, `canonical_sqlite_projection=missing`,
  `legacy_sqlite_projection=evidence_present_not_current_consumer`,
  `chat_synthesis=DATA_MISSING`, and `projection_repair=not_run`.
- The safest extension was report-only because the required labels could be
  published from integrated smoke artifacts without route behavior changes.

## Speculative

- A future Cockpit/backend status endpoint could expose the same category split,
  but that is a separate exact-file implementation task.
- Projection repair may require a future approved rebuild, backfill, resync, or
  source decision. None was run here.

## DATA_MISSING

- Fresh live route health after the integrated 2026-05-25T13:45:28+10:00 smoke
  was not re-smoked by the child.
- Live chat synthesis behavior for A2M is unproven because chat/session paths
  may write state.
- The future canonical SQLite projection source path remains unapproved.

## Validation

- Controller task-card validation: pass.
- A2M audit task-card validation: pass.
- A2M smoke controller task-card validation: pass.
- A2M read-only smoke task-card validation: pass.
- Child task-card validation: pass.
- JSON validation for integrated A2M artifacts: pass.
- JSON validation for child status artifacts: pass.
- `git diff --check HEAD~2..HEAD`: pass for the cherry-picked commits.
- `git diff --check`: pass for current worktree changes.
- Registry `list-active`: active Reporting hygiene job observed on unrelated
  files.
- Registry claim/check-overlap for this controller and child were blocked only
  by known external dirty task cards, plus the parent controller card during
  child validation. This was classified as preserved external dirt rather than
  an A2M file conflict.

## Changed Files

Integrated commits added:

- `docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md`
- `docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md`
- `docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/*`
- `reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/*`
- `reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/*`

Controller and child added:

- `docs/agent_tasks/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525.md`
- `reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/README.md`
- `reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/status.json`
- `reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/validation.json`
- `reports/agent_jobs/a2m_news_projection_canonical_integration_and_status_reporting_v1_20260525/diff-check.json`
- `docs/agent_tasks/a2m_news_projection_status_reporting_safe_extension_v1_20260525.md`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/*`

## Active Jobs And Safe Isolation

The shared registry was reachable at
`/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`. Active jobs observed during
the run were Reporting-lane hygiene/design jobs on unrelated `merge_parking` or
`worktree_taskcard_hygiene` paths. No active job owned the A2M integration or
child report paths.

The integration ran in canonical because exact paths were disjoint. The parked
isolated worktree remains intact.

## Final Worktree Status

Expected after committing this controller report and the child report: only the
two known foreign task cards should remain untracked.

## Project Memory Save Recommendation

Save: A2M route health is split. Canonical now contains the May 25 A2M audit and
read-only smoke reports. A2M was visible through Qdrant-backed `/rag/query` in
the integrated smoke, canonical NVMe SQLite projection files were absent, legacy
`/mnt/sdb2` SQLite had A2M evidence but is not the current consumer, Cockpit
status routes were 404, chat synthesis remained `DATA_MISSING`, and no data
repair or projection rebuild was run.
