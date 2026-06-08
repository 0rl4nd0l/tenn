# Control Plane Sloppy Fix Live Proof V1

## Objective

Prepare milestone 3 from `plan.html`: validate Sloppy on a real issue run after
the milestone-2 fail-closed workflow patch. This report is approval-gated and
does not perform GitHub writes.

## Current State

WAITING_ON_USER

## Constraints And Unsafe Actions

- Preserve dirty shared checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Candidate patch worktree:
  `/home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607`.
- Do not push, dispatch/rerun Actions, mutate PRs/issues, merge, rebase, reset,
  clean, prune, or delete worktrees/branches without explicit approval.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  production data.

## Evidence Used

- Dirty checkout preflight on 2026-06-08 Australia/Melbourne:
  - path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  - branch: `tmp/sloppy-fix-demo`
  - HEAD: `dfa313aaa6c1b34696f4bf9a8bd430636e5792ce`
  - status: still dirty with unrelated runtime/news/provider/UI artifacts; not
    edited.
- Candidate patch worktree:
  - branch: `safe/sloppy-fix-provider-failclosed-v1-20260607`
  - HEAD/base: `7443d9f248346210ada834e1fd19ab923ace192f`
  - current local patch: `.github/workflows/sloppy-fix.yml` modified plus
    `scripts/test_sloppy_fix_workflow.py`, task card, and `plan.html`
    untracked.
- Proof PR #307:
  - URL: `https://github.com/0rl4nd0l/tenn/pull/307`
  - state: open
  - title: `[Evaluation] Disposable Sloppy live-fix proof`
  - head branch: `safe/sloppy-fix-live-fix-proof-v1-20260607`
  - head SHA: `b3d0e9b1d73ed0794a151c530f0e592797afde90`
  - merge state: `CLEAN`
  - current check rollup: Sloppy Scan `SUCCESS`
  - hard boundary: do not merge this PR.
- Prior Sloppy Scan run:
  - run: `https://github.com/0rl4nd0l/tenn/actions/runs/27084910196`
  - event: `pull_request`
  - head branch: `safe/sloppy-fix-live-fix-proof-v1-20260607`
  - head SHA: `b3d0e9b1d73ed0794a151c530f0e592797afde90`
  - conclusion: `success`
  - log evidence: found 3 issues, wrote `/tmp/sloppy-scan-issues.json`, uploaded
    artifact `sloppy-scan-issues`.
  - artifact: ID `7461440575`, not expired, size `465` bytes.
- Downloaded read-only artifact copy:
  `/tmp/tenn-sloppy-proof-27084910196/sloppy-scan-issues.json`.
  It contains 3 `status: found` issues in `sloppy-proof-intentional-issue.js`:
  one `stubs` issue and two `lint` issues.
- Prior downstream Sloppy Fix run:
  - run: `https://github.com/0rl4nd0l/tenn/actions/runs/27084915118`
  - event: `workflow_run`
  - workflow HEAD: `94194de0e1b005ae5b00087645900a953b06c1de`
  - conclusion: `success`
  - jobs: `fix` success, `comment` success.
  - log evidence: loaded 3 preexisting issues from
    `/tmp/sloppy-scan/sloppy-scan-issues.json`, skipped independent rescan,
    skipped all 3 with `Could not parse agent output`, pass summary `0 fixed`
    and `3 skipped`, final summary `Fixed 0` and `Skipped 3`.
- Local milestone-2 validation already proved the candidate workflow would fail
  closed for seeded positive findings plus `issues-fixed=0`; live proof is still
  `DATA_MISSING` until the patch is pushed and exercised.

## Files Touched

- `docs/agent_tasks/control_plane_sloppy_fix_live_proof_v1_20260608.md`
- `reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/README.md`
- `reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/validation.json`
- `reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/diff-check.json`

## Files Intentionally Not Touched

- Dirty shared checkout files.
- `.github/workflows/sloppy-scan.yml`
- `.sloppy.yml`
- PR #307.
- GitHub issues.
- Runtime data, DBs, Qdrant, Redis, news stores, source PDFs, gold labels,
  extraction prompts, parser routing, model/GPU config, and backfills.

## Commands Run

- `pwd`: exit 0.
- `git branch --show-current`: exit 0.
- `git rev-parse HEAD`: exit 0.
- `git status --short --untracked-files=all`: exit 0.
- `sed -n '1,240p' plan.html`: exit 0.
- `gh pr view 307 --json ...`: first attempt exit 1 due unsupported
  `headRefOid`; corrected command exit 0.
- `gh run view 27084915118 --json ...`: first attempt exit 1 due unsupported
  `jobs`; corrected command exit 0.
- `gh run view 27084910196 --json ...`: first attempt exit 1 due unsupported
  `jobs`; corrected command exit 0.
- `gh api repos/0rl4nd0l/tenn/actions/runs/27084910196/artifacts --jq ...`:
  exit 0.
- `gh api repos/0rl4nd0l/tenn/actions/runs/27084915118/jobs --jq ...`: exit 0.
- `gh run download 27084910196 -n sloppy-scan-issues -D /tmp/tenn-sloppy-proof-27084910196`: exit 0.
- `gh run view 27084915118 --log | rg ...`: exit 0.
- `gh run view 27084910196 --log | rg ...`: exit 0.
- `python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_sloppy_fix_live_proof_v1_20260608.md --write-report`: exit 0.
- `python3 scripts/test_sloppy_fix_workflow.py`: exit 0; 4 tests passed.
- `python3 -c "import pathlib, yaml; ..."` YAML parse: exit 0; `YAML OK`.
- `git diff --check`: exit 0.
- `python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_sloppy_fix_live_proof_v1_20260608.md --repo-root .`: exit 0; no disallowed files.

## Approvals Needed

WAITING_ON_USER
Needed: explicit approval to push the candidate Sloppy Fix fail-closed branch
and run a bounded live proof against PR #307.
Why: GitHub `workflow_run` behavior cannot be proven from local static checks;
the fail-closed workflow must execute in GitHub Actions against a seeded scan.
Current safe state: local patch and tests are complete; prior live evidence
proves the exact failure mode, but no GitHub write was performed.
Options: A) approve push plus bounded rerun/dispatch proof, B) review the local
diff first and defer live proof, C) skip Sloppy live proof and move to another
milestone with this gate still `DATA_MISSING`.
Recommended: A.

## Proposed Approval Command Sequence

Run only after explicit approval:

```bash
cd /home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607
python3 scripts/test_sloppy_fix_workflow.py
python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/sloppy-fix.yml').read_text(encoding='utf-8')); print('YAML OK')"
git diff --check
python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md --repo-root .
git push -u origin safe/sloppy-fix-provider-failclosed-v1-20260607
```

Then perform one bounded GitHub-side proof. The preferred proof is to open a PR
from `safe/sloppy-fix-provider-failclosed-v1-20260607` to `main`, wait for the
workflow to exist on a GitHub-visible branch, then rerun or trigger Sloppy Scan
for PR #307 and inspect the downstream Sloppy Fix result. Exact dispatch/rerun
command should be selected after re-checking GitHub state at approval time.

## Blocked Items And DATA_MISSING

- Live Sloppy Fix run using the candidate fail-closed workflow:
  `DATA_MISSING`.
- Whether the live result is a deliberate failed status for 3 seeded/0 fixed:
  `DATA_MISSING`.
- `actionlint`: `DATA_MISSING`; not installed locally.

## Validation Status

- Task-card validation: passed using the sibling agent-contract validator.
- Read-only PR #307 state refresh: passed.
- Read-only prior Sloppy Scan/Fix run refresh: passed.
- Prior scan artifact evidence: passed; artifact has 3 `status: found` issues.
- Prior fix failure-mode evidence: passed; old workflow loaded 3, fixed 0,
  skipped 3, and still completed success.
- Local candidate workflow tests: passed; 4 tests.
- YAML parse: passed.
- `git diff --check`: passed.
- Task-card `check-diff`: passed with no disallowed files.
- Live GitHub proof: `DATA_MISSING` pending explicit approval.

## Raw Logs

- Raw logs were not persisted under `reports/`; the relevant log lines are
  summarized above. The downloaded proof artifact copy is under `/tmp` and may
  be ephemeral.

## Unsafe Actions Avoided

- No GitHub push.
- No workflow dispatch/rerun.
- No PR or issue mutation.
- No runtime/service/data mutation.
- No dirty checkout edits.

## Ignored Or Untracked Artifact Note

- The milestone-3 report directory is ignored by Git. The task card includes the
  current milestone-2 local patch files in `allowed_files` because this
  approval packet lives on top of that local candidate branch; it does not
  authorize further edits to those files without a new task card or explicit
  approval.

## Remaining Risk

- Static and historic run evidence prove the old failure mode and the local
  intended gate, but production behavior is not proven until GitHub Actions runs
  the patched workflow.

## Next Recommended Prompt

`Approved: push safe/sloppy-fix-provider-failclosed-v1-20260607 and perform one bounded Sloppy live proof against PR #307; do not merge PR #307.`
