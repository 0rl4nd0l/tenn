# Control Plane Docs Skills Surface Stale Report Cleanup

Job id: `control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623`

Status: validation passed; local commit refreshed onto current migration
baseline and ready for focused PR.

Task card:
`docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md`

## Repo State

- Requested cwd:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Requested cwd finding: invalid/copied git snapshot. It has an empty `.git`
  directory and Git reports "not a git repository".
- Working repo:
  `/home/l4nd0/tenn-control-plane-docs-skills-surface-stale-report-cleanup-v1-20260623`
- Branch:
  `control-plane/docs-skills-surface-stale-report-cleanup-v1-20260623`
- Rebased from original local commit:
  `a65d80c41e13d8ef22267714b26cb476cd66eb18`
- Rebased onto:
  `b58c9f1ce79b5e9583b1b30cf98b3507867f0aeb`
- Closeout commit subject:
  `docs(control-plane): refresh skills surface and PR report states`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Merge-base after refresh:
  `b58c9f1ce79b5e9583b1b30cf98b3507867f0aeb`
- Remote note:
  after refresh this branch is 1 commit ahead and 0 commits behind
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.

## Registry

- `list-active --read-only`: passed, no active jobs before claim.
- `check-overlap`: passed, no overlap issues.
- Claim: succeeded for this job, then refreshed after task-card allowlist
  tightening.
- Release: succeeded after validation.
- Registry root:
  `/home/l4nd0/tenn-extraction-handoff-continuation-v1-20260621/.git/tenn-agent-registry`

## Files Inspected

- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- `reports/agent_jobs/control_plane_orlando_audit_v1_20260622/README.md`
- `reports/agent_jobs/control_plane_orlando_audit_v1_20260622/RECENT_WORK_SEARCH.md`
- `reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/README.md`
- `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/README.md`
- `reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/handoff/HANDOFF.md`
- `reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/HANDOFF.md`

## Files Changed

- `docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/dev_flow/CONTROL_PLANE_PR_STATE_REFRESH.md`
- `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- this report bundle

## Corrected Stale References

- `SKILLS_SURFACE.md` freshness metadata no longer points at older PR #386
  evidence only; after refresh it cites current canonical commit `b58c9f1c`,
  PR #397, and visible skill count 10.
- `CONTROL_PLANE_STATUS.md` no longer says the skill-surface guide needs the
  pending-PR #380 metadata refresh.
- `CONTROL_PLANE_OPEN_WORK.md` no longer lists SKILLS_SURFACE freshness refresh
  as open work.
- A current PR-state index now records live state for PR #378, #380, #373, and
  #367 at `docs/dev_flow/CONTROL_PLANE_PR_STATE_REFRESH.md`.
- Historical report bundles with old PR state were not edited; they are
  identified in `stale_reference_matrix.json` and current searches should use
  the new PR-state refresh page.

## Live PR Evidence

| PR | State | Evidence |
| --- | --- | --- |
| #378 | MERGED | merged `2026-06-18T10:06:35Z`, merge commit `f44803bba049ea1d2cfe9341b0f9af4379736bdf` |
| #380 | MERGED | merged `2026-06-22T00:04:48Z`, merge commit `4d62fec4e855b313ae89136e947510c627b9bcde` |
| #373 | MERGED | merged `2026-06-18T05:50:15Z`, merge commit `98e632996aae3bff82627a02b75e64cddd927420` |
| #367 | CLOSED, SUPERSEDED | no merge commit; superseded by merged PR #375 plus PR #377 |
| #375 | MERGED | merged `2026-06-18T08:21:31Z`, merge commit `acb7e9a7df6a9b75d14beff16c750693a4aab5e6` |
| #377 | MERGED | merged `2026-06-18T08:35:49Z`, merge commit `bae8eda25633cf651849c5681d7ffcb00160fbf9` |

## SKILLS_SURFACE Freshness Evidence

- `last_verified_at`: `2026-06-23T09:23:26Z`
- `last_verified_commit`: `b58c9f1ce79b5e9583b1b30cf98b3507867f0aeb`
- `last_verified_pr`: `397`
- `maintenance`: `hand_maintained`
- visible skill count: `10`
- `DATA_MISSING`: host picker/autocomplete visibility was not probed.

## Validation Results

All validation below passed unless explicitly marked unavailable:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim ... --repo-root .`
- `python3 scripts/agent_job_registry.py release control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623 --repo-root .`
- final `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: passed with no active jobs.
- `gh pr view 378/380/373/367 --json number,state,mergedAt,mergeCommit,title,headRefName,baseRefName,url`
- `python3 -m json.tool` for `status.json`, `stale_reference_matrix.json`, and `skills_surface_freshness_audit.json`
- `rg` stale-phrase check: editable docs clean; stale phrases remain only in out-of-scope historical report bundles.
- `scripts/check_markdown_hygiene.sh`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md --repo-root . --no-write-report`
- `git diff --check`
- `git diff --cached --check`
- `markdownlint`: unavailable as a local binary; repo markdown link/path hygiene passed.
- Rebase refresh: `git rebase origin/migration/clean-runtime-baseline-reconstruct-v1`
  completed after docs-only conflict resolution in `SKILLS_SURFACE.md` and
  `CONTROL_PLANE_STATUS.md`.

## Remaining DATA_MISSING

- Host picker/autocomplete visibility for repo-backed skills was not probed.
- Historical report bundles were not rewritten; they remain append-only
  historical artifacts.

## Deferred Follow-Up

- Next narrow cleanup candidate: repair and verify Git hook installation path
  behavior across Tenn worktrees.
- Optional later cleanup: add archival banners to old PR #378/#380/#373/#367
  report bundles if report-search confusion persists.
- Do not use this task to fix `/goal monitor`, hook scripts, legacy
  `.codex/skills`, or `.claude/monitors`.

## Final Git Status

After the rebase refresh and validation, `git status --short
--untracked-files=all` was clean before push.

## Save Recommendation

Focused PR candidate:
`docs(control-plane): refresh skills surface and PR report states`
