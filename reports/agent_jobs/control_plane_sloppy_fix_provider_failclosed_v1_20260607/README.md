# Control Plane Sloppy Fix Provider Failclosed V1

## Objective

Proceed with milestone 2 from `plan.html`: make Sloppy Fix fail closed when a
seeded scan finds issues but Sloppy Fix fixes zero, using TDD, without touching
the dirty shared checkout or pushing/dispatching GitHub Actions.

## Current State

DONE_WITH_RISK

## Constraints And Unsafe Actions

- Preserve dirty shared checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Work in clean sibling:
  `/home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607`.
- Do not push, dispatch Actions, merge PRs, or edit GitHub issues without
  explicit approval.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  production data.

## Evidence Used

- Dirty checkout preflight:
  - `pwd`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - branch: `tmp/sloppy-fix-demo`
  - HEAD: `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
  - dirty files include workflow-adjacent news/provider changes, runtime DBs,
    and untracked task/skill artifacts; this checkout was not edited.
- Clean worktree preflight:
  - path: `/home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607`
  - branch: `safe/sloppy-fix-provider-failclosed-v1-20260607`
  - HEAD: `7443d9f248346210ada834e1fd19ab923ace192f`
  - status before this task: only `plan.html` untracked.
- `git ls-remote origin refs/heads/main` returned
  `7443d9f248346210ada834e1fd19ab923ace192f`.
- Current open PR evidence includes PR #307
  `[Evaluation] Disposable Sloppy live-fix proof`, still open and not to merge.
- Recent Sloppy Fix runs on `main` are completing successfully, including
  workflow_run runs at main HEAD `7443d9f2`; live proof of fixed issue counts is
  not yet available in this local-only task.
- `/tmp/sloppy-action/action.yml` exposes action output `issues-fixed`.

## Files Touched

- `.github/workflows/sloppy-fix.yml`
- `scripts/test_sloppy_fix_workflow.py`
- `docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md`
- `reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/README.md`
- `reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/validation.json`
- `reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/diff-check.json`

## Files Intentionally Not Touched

- Dirty shared checkout files.
- `.github/workflows/sloppy-scan.yml`
- `.sloppy.yml`
- Pre-existing untracked `plan.html` resume artifact.
- Runtime data, DBs, Qdrant, Redis, news stores, source PDFs, gold labels,
  extraction prompts, parser routing, model/GPU config, and backfills.

## Commands Run

- `pwd`: exit 0.
- `git branch --show-current`: exit 0.
- `git rev-parse HEAD`: exit 0.
- `git remote -v`: exit 0.
- `git status --short --untracked-files=all`: exit 0.
- `sed -n '1,220p' /home/l4nd0/.codex/skills/tdd/SKILL.md`: exit 0.
- `sed -n '1,260p' plan.html`: exit 0.
- `sed -n '261,520p' plan.html`: exit 0.
- `git worktree list --porcelain`: exit 0, output summarized.
- `gh pr list --state open --limit 40 --json ...`: exit 0.
- `gh run list --workflow "Sloppy Fix" --limit 10 --json ...`: exit 0.
- `gh run list --workflow "Sloppy Scan" --limit 10 --json ...`: exit 0.
- `git ls-remote origin refs/heads/main`: exit 0.
- `python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md --write-report`: exit 0.
- RED: `python3 scripts/test_sloppy_fix_workflow.py`: exit 1; failed because the workflow lacked `Fail Sloppy fix when seeded issues remain unfixed`.
- GREEN: `python3 scripts/test_sloppy_fix_workflow.py`: exit 0; 4 tests passed after the workflow patch and review fix.
- `python3 -c "import pathlib, yaml; ..."` YAML parse: exit 0; `YAML OK`.
- `git diff --check`: exit 0.
- `command -v actionlint`: exit 1; `actionlint` unavailable.
- `python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md --repo-root .`: exit 0; no disallowed files.

## Approvals Needed

- GitHub push or workflow dispatch approval is not granted and was not used.

## Blocked Items And DATA_MISSING

- Live GitHub Actions proof after this patch: `DATA_MISSING` until push/dispatch
  is explicitly approved and performed.
- `actionlint`: `DATA_MISSING` until installed or available.

## Validation Status

- Task-card validation: passed using sibling validator at
  `/home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py`.
- RED test: passed as a RED signal; initial focused test failed because the
  fail-closed gate was absent.
- GREEN test: passed; `python3 scripts/test_sloppy_fix_workflow.py` ran 4 tests.
- YAML parse/static checks: passed.
- Post-change code review: found a GitHub Actions hyphenated-output expression
  issue; fixed by using bracket notation for `issues-fixed` and reran tests.
- `git diff --check`: passed.
- Task-card `check-diff`: passed with no disallowed files.
- `actionlint`: `DATA_MISSING`; not installed.

## Raw Logs

- No raw logs captured yet; command outputs are short enough to summarize here.

## Unsafe Actions Avoided

- No dirty checkout edits.
- No GitHub writes.
- No runtime/service/data mutation.

## Ignored Or Untracked Artifact Note

- `plan.html` is a pre-existing untracked resume artifact in the clean worktree
  and is included in the task allowlist so diff validation can remain literal.

## Remaining Risk

- Local static tests can prove the workflow contract shape, but production
  readiness still requires a live Sloppy Scan -> Sloppy Fix run after the patch
  lands on a branch/default surface where Actions can execute it.
- Recent live Sloppy Fix runs are still green on `main`; this patch has not been
  pushed or dispatched, so the live fail-closed behavior is not yet proven.

## Next Recommended Prompt

`Approve a bounded push/dispatch proof for the Sloppy Fix fail-closed branch, or continue locally with the next production-readiness milestone after reviewing this report.`
