# Two-Shot Dev-Flow Control Surface V1

## Objective

Update Tenn development workflow and control-plane guidance so non-trivial Git
Hygiene and control-plane remediation default to two-shot workstreams with clear
autonomy profiles instead of micro-approval loops for safe report-local and
preservation-only actions.

## Evidence Used

- Clean worktree:
  `/home/l4nd0/tenn-two-shot-dev-flow-control-surface-current-base-v1-20260607`.
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `07bdfe6d84eeba41c357eaf5893420ef77189625`.
- Replayed exact six-file patch from local source commit
  `2c067c363122642782d9d29f61966e281ee85bdd` onto the current remote base
  without merge, rebase, or cherry-pick.
- Required registry preflight passed in the clean worktree with
  `read_only: true`, `lock_acquired: false`, and no active jobs.
- Dirty source-checkout registry preflight was `DATA_MISSING` because that
  checkout's script rejected `--read-only`; no lock-taking fallback was run.
- `AGENTS.md`.
- `.agents/skills/tenn-git-hygiene/SKILL.md`.
- `.agents/skills/tenn-goal-report/SKILL.md`.
- `.agents/skills/tenn-frame-design/SKILL.md`.
- Read-only evidence from
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/live_branch_two_shot_remediation_manifest_v1_20260607/README.md`.
- Read-only evidence from
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/live_branch_two_shot_remediation_manifest_v1_20260607/APPROVAL_MANIFEST.md`.
- Read-only evidence from
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/live_branch_two_shot_remediation_manifest_v1_20260607/EXECUTION_PLAN_FOR_SHOT_2.md`.
- Read-only Shot 2 closeout evidence under
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/agent_jobs/live_branch_two_shot_remediation_manifest_v1_20260607/shot2_closeout_20260607T203939+1000/`.

## Files Changed

- `AGENTS.md`
- `.agents/skills/tenn-git-hygiene/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `.agents/skills/tenn-frame-design/SKILL.md`
- `docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md`
- `reports/agent_jobs/two_shot_dev_flow_control_surface_v1_20260607/README.md`

## AGENTS.md Updates

- Added `Two-Shot Workstreams And Autonomy Envelopes`.
- Defined Shot 1 as investigate, classify, preserve safe evidence, create
  approval manifest, create execution plan, and stop.
- Defined Shot 2 as execute approved manifest groups mechanically, skip drifted
  paths, stop before forbidden boundaries, and close out.
- Reserved `WAITING_ON_USER` for real boundary crossings, ambiguity, missing
  approval, or unsafe drift.

## Skill Updates

- `tenn-git-hygiene` now defaults non-trivial Git Hygiene and control-plane
  remediation to two-shot workstreams.
- `tenn-goal-report` now points long `/goal` runs with many files, mixed-risk
  dirt, cleanup/remediation, or repeated tiny approval loops to two-shot mode.
- `tenn-frame-design` now asks Frames for Git Hygiene/control-plane remediation
  to define autonomy profile, approval boundary, Shot 1/Shot 2 split, stop
  states, and owner-decision classes.

## Autonomy Profiles Added

- `REPORT_AUTONOMY`
- `PRESERVATION_AUTONOMY`
- `GENERATED_CLEANUP_AUTONOMY`
- `OWNER_APPROVAL_REQUIRED`

## Validation

| command | exit status | result |
| --- | ---: | --- |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | clean-worktree registry read-only preflight passed with `read_only: true`, `lock_acquired: false`, and no active jobs |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` in dirty source checkout | 2 | `DATA_MISSING`; script rejected `--read-only`; no lock-taking fallback was run |
| skill frontmatter parse for changed skills | 0 | `name` and `description` present for `tenn-git-hygiene`, `tenn-goal-report`, and `tenn-frame-design` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md` | 0 | task card valid |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md --no-write-report` | 0 | all staged changed files are allowlisted, including the forced-added report |
| `git diff --check` | 0 | no whitespace errors |
| `git diff --check --cached` | 0 | no staged whitespace errors |
| changed-path guard | 0 | only allowlisted control-plane files changed; no product/runtime/extraction paths changed |
| `git status --short --branch --untracked-files=all` | 0 | current-base replay branch is clean after commit |

## Unsafe Actions Avoided

- no product/backend/frontend/runtime/data/extraction implementation edits
- no DB, Qdrant, news, memory, backfill, source-PDF, gold-label, prompt,
  service, runtime/model/GPU config, production-data, or live-service mutation
- no dependency install
- no `git clean`
- no `git reset --hard`
- no stash or stash drop
- no branch deletion
- no worktree removal
- no rebase, merge, cherry-pick, force-push, or GitHub mutation beyond the
  explicitly approved branch push and PR creation
- no Git Hygiene cleanup wave
- no dirty live-branch mutation

## Ready For Commit/PR

- Ready for local commit: yes.
- Ready for PR: yes after local validation on the current-base replay branch.

## Next Recommended Step

Review the PR and wait for acceptable CI/review before merge.
