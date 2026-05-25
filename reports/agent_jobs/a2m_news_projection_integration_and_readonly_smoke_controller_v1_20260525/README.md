# A2M Projection Integration And Read-Only Smoke Controller

Generated: 2026-05-25T13:45:28+10:00

## Phase Summaries

### Phase 0: Preflight

- Canonical `/home/l4nd0/tenn` resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch at preflight: `migration/clean-runtime-baseline-reconstruct-v1`.
- Canonical HEAD at preflight: `6eb30d3f098849c501d2239a188374bd822d6000`.
- Canonical dirty state at preflight: two unrelated untracked task cards:
  - `docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md`
  - `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`
- Task-card and registry command syntax was verified from current help and `AGENTS.md`.
- Merge-parking command syntax is DATA_MISSING: no repo command or config entry for a merge-parking tool was found. Parking was therefore implemented as preserved branch/worktree state.
- Controller card validated in canonical, but canonical `check-overlap` failed because of the two unrelated untracked task cards.
- Safe isolation was used: `/home/l4nd0/tenn-a2m-news-projection-controller-v1-20260525` on branch `safe/a2m-news-projection-integration-readonly-smoke-controller-v1-20260525`.
- Controller card validated and claimed successfully in the isolated worktree.

### Phase 1: A2M Audit Integration

- Source audit worktree was clean: `/home/l4nd0/tenn-a2m-news-projection-path-remediation-v1-20260525`.
- Source audit HEAD matched `3eb87220b3834ecd510202118d0c1820d7f9aa36`.
- The source commit added only the nine expected A2M task/report artifacts.
- The isolated controller worktree had no tracked or untracked files at those A2M audit paths.
- The audit commit was cherry-picked with `-x` into the isolated controller branch as `2d1e810bcb978cc062d5de81d2c6b6198a76b8a4`.
- Integration status: parked integration candidate, not direct canonical-branch integration, because canonical registry overlap was blocked by unrelated dirty task cards.

### Phase 2: Read-Only Smoke

- Smoke task card validated.
- A standalone smoke claim was not attempted because the active controller already owns the smoke files; standalone `check-overlap` correctly reported a self-owned nested overlap.
- Qdrant `news_chunks` is live and contains A2M evidence.
- Backend `/rag/query` and Cockpit/Next `/rag/query` returned A2M news results.
- Canonical NVMe SQLite projection files are absent.
- Legacy `/mnt/sdb2` SQLite files contain A2M evidence but are not current canonical consumers.
- Cockpit config/status visibility is incomplete: `/api/cockpit/config` is reachable, while `/api/cockpit/news/status` and `/api/cockpit/status` returned 404.

### Phase 3: Optional Child

No optional child safe-extension was run. The smoke proves a safe next action exists, but the smallest correct next step should be a separate exact-files task card after this controller: `a2m_news_projection_status_reporting_safe_extension_v1_20260525`.

## Confirmed

- The completed A2M audit commit was preserved and cherry-picked in a clean isolated branch.
- Canonical direct integration was unsafe under current registry protocol because canonical `check-overlap` was dirty-file blocked.
- A2M is currently user-visible through the Qdrant-backed news query route.
- Missing canonical SQLite projection files remain real.
- Legacy SQLite evidence is provenance only unless a separate approved task changes the current consumer path.
- No forbidden data mutation, Qdrant write, DB write, service restart, ingestion, backfill, resync, reindex, or projection rebuild was run.

## Inferred

- The immediate user-facing problem is status/provenance clarity rather than complete A2M news invisibility.
- A later data repair or projection rebuild may be needed for parity, but it is not justified as the next smallest safe step from this smoke alone.

## Speculative

- The exact desired long-term canonical SQLite projection source path remains open and should not be guessed.

## DATA_MISSING

- Exact live chat synthesis answer behavior for A2M was not tested because chat/session paths may write state.
- Repo-native merge parking command syntax was not found.
- Final direct canonical integration remains pending until canonical dirty-file blockers are resolved or a merge-back approval is given.

## Changed Files

- Cherry-picked audit artifacts:
  - `docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md`
  - `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/*`
- Controller artifacts:
  - `docs/agent_tasks/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525.md`
  - `reports/agent_jobs/a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525/*`
- Smoke artifacts:
  - `docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`
  - `reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/*`

## Validation

- Controller task-card validate: pass.
- Isolated controller `check-overlap`: pass before claim.
- Controller registry claim: pass.
- Audit card validate: pass.
- Audit JSON artifacts: pass.
- Audit cherry-pick `git diff --check HEAD~1..HEAD`: pass.
- Smoke card validate: pass.
- Qdrant read-only checks: pass.
- SQLite read-only checks: pass.
- Backend and Next read-only route checks: pass.
- Final JSON validation, `git diff --check`, `check-diff`, commit, release, and final status are recorded in `validation.json` and final closeout.

## Active Jobs And Isolation

- Own active controller: `a2m_news_projection_integration_and_readonly_smoke_controller_v1_20260525`.
- Non-owned Reporting job `reporting_ui_safe_issue_fixes_v1_20260525` was active earlier and file-disjoint; it was no longer active in the final registry list.
- Non-owned active Evaluation job in the final registry list: `strategy_lab_quantdinger_repeatability_harness_v1_20260525`, file-disjoint.
- The earlier referenced `strategy_lab_quantdinger_readonly_transport_progress_v1_20260525` was not active in live registry checks during this controller run.

## Final Worktree Status

Final worktree status is recorded after validation. At report generation time, only owned controller/smoke task cards and ignored report artifacts were dirty, plus the already-committed A2M audit cherry-pick.

## Project Memory Save Recommendation

Save to Project Memory: A2M is currently reachable through Qdrant-backed `/rag/query` even while canonical NVMe SQLite projection files are absent; future status/reporting must distinguish Qdrant retrieval health, canonical SQLite projection health, and legacy `/mnt/sdb2` provenance.
