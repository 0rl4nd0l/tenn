# Changed Docs Summary

## Changed Files

- `docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md`
  - Created the validated task card for this safe-extension docs cleanup.
- `docs/dev_flow/SKILLS_SURFACE.md`
  - Replaced stale freshness metadata with current commit/PR/time evidence,
    refreshed after rebase to canonical commit `b58c9f1c` / PR #397.
  - Marked the file hand-maintained.
  - Recorded host picker/autocomplete visibility as `DATA_MISSING`.
  - Added refresh instructions and `stale_if_files`.
- `docs/dev_flow/CONTROL_PLANE_PR_STATE_REFRESH.md`
  - Added a current docs index for PR #378, PR #380, PR #373, and PR #367.
  - Recorded live GitHub state and how to treat old report-bundle hits.
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
  - Updated the status header to current canonical evidence after the branch
    refresh.
  - Changed the skill-surface guide row from stale/partial to current for
    repo-visible freshness.
  - Pointed historical PR-state lookup at the new PR refresh page.
- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
  - Marked SKILLS_SURFACE freshness cleanup implemented.
  - Reframed old report-state conflicts as indexed in current docs while
    preserving old report bundles as append-only/historical.
  - Left archival report banners as a separate follow-up.

## Report Artifacts

- `reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/README.md`
- `reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/status.json`
- `reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/stale_reference_matrix.json`
- `reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/skills_surface_freshness_audit.json`
- `reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/changed_docs_summary.md`

## Scope Guard

No Tenn product/runtime code, extraction logic, financial truth, parser routing,
database, Qdrant, news, memory store, migration, hook implementation, CI
workflow, source document, or production data file was changed.

Historical reports containing old PR states were inspected but not edited
because they are outside this task-card edit scope.
