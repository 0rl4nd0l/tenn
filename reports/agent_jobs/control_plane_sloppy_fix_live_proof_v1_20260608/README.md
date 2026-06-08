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
- User approval:
  - 2026-06-08: user said `proceed` after the report recommended approving a
    push plus one bounded live proof.
- Candidate branch publication:
  - commit: `d95162229e7f2560781afe9336024f642376dcea`
  - branch pushed: `safe/sloppy-fix-provider-failclosed-v1-20260607`
  - PR: `https://github.com/0rl4nd0l/tenn/pull/321`
  - PR #321 state after creation: open, base `main`, head
    `safe/sloppy-fix-provider-failclosed-v1-20260607`, merge state `CLEAN`.
- GitHub Actions trigger constraint:
  - GitHub Docs record `workflow_run` as a default-branch workflow event:
    `https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run`.
  - Observed evidence matches this: downstream Sloppy Fix run `27109633518`
    reports `headBranch=main` and `headSha=7443d9f248...`, while its checkout
    step checked out the triggering scan SHA `d9516222`.
- PR #321 Sloppy Scan run:
  - run: `https://github.com/0rl4nd0l/tenn/actions/runs/27109627103`
  - event: `pull_request`
  - head branch: `safe/sloppy-fix-provider-failclosed-v1-20260607`
  - head SHA: `d95162229e7f2560781afe9336024f642376dcea`
  - conclusion: `success`
  - artifact: `sloppy-scan-issues`, ID `7469494089`, not expired, size
    `250` bytes.
  - downloaded artifact copy:
    `/tmp/tenn-sloppy-proof-27109627103/sloppy-scan-issues.json`.
  - artifact payload: `score=100`, `issues=[]`.
- PR #321 downstream Sloppy Fix run:
  - run: `https://github.com/0rl4nd0l/tenn/actions/runs/27109633518`
  - event: `workflow_run`
  - workflow HEAD: `7443d9f248346210ada834e1fd19ab923ace192f`
  - conclusion: `success`
  - jobs: `fix` success, `comment` success.
  - log evidence: checkout reached `d9516222`, then `Skip sloppy fix (no scan
    issues)` ran because the triggering PR #321 scan reported zero issues.
  - result: this did not exercise the seeded-positive zero-fix fail-closed gate.
- Requested PR #307 live proof remains `DATA_MISSING`: rerunning PR #307 before
  PR #321 lands on `main` would exercise the old default-branch workflow, not
  the patched workflow definition.

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
- `git commit -m "Fail Sloppy Fix on zero seeded fixes"`: exit 0; created
  `d95162229e7f2560781afe9336024f642376dcea`.
- `git push -u origin safe/sloppy-fix-provider-failclosed-v1-20260607`: exit 0.
- `gh pr create --base main --head safe/sloppy-fix-provider-failclosed-v1-20260607 ...`: exit 0; created PR #321.
- `gh pr view 321 --json ...`: exit 0.
- `gh run list --workflow "Sloppy Scan" --limit 12 --json ...`: exit 0.
- `gh run list --workflow "Sloppy Fix" --limit 12 --json ...`: exit 0.
- `gh run watch 27109633518 --interval 5 --exit-status`: exit 0; run completed
  success.
- `gh run view 27109633518 --json ...`: exit 0.
- `gh api repos/0rl4nd0l/tenn/actions/runs/27109627103/artifacts --jq ...`:
  exit 0.
- `gh run download 27109627103 -n sloppy-scan-issues -D /tmp/tenn-sloppy-proof-27109627103`: exit 0.
- `gh run view 27109633518 --log | rg ...`: exit 0.
- `gh run view 27109627103 --log | rg ...`: exit 0.
- `gh api repos/0rl4nd0l/tenn/actions/runs/27109633518/jobs --jq ...`: exit 0.

## Approvals Needed

WAITING_ON_USER
Needed: explicit approval for the next GitHub write strategy: merge PR #321 to
`main` or choose an alternate default-branch proof mechanism.
Why: `workflow_run` uses the default-branch workflow definition; PR #321's
branch workflow was visible, but the downstream run did not exercise the patched
zero-fix gate and PR #307 cannot prove it until the patched workflow is on
`main`.
Current safe state: candidate branch was pushed, PR #321 was opened, PR #321's
Sloppy Scan/Fix ran successfully with zero findings, and no merge was performed.
Options: A) approve merge of PR #321 to `main`, then rerun/trigger Sloppy Scan
on PR #307 and verify downstream Sloppy Fix fails closed, B) keep PR #321 open
for review and leave live proof `DATA_MISSING`, C) design a separate temporary
default-branch proof mechanism/task card.
Recommended: A, if PR #321 checks and review are acceptable.

## Proposed Approval Command Sequence

Already completed after `proceed` approval:

```bash
cd /home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607
python3 scripts/test_sloppy_fix_workflow.py
python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/sloppy-fix.yml').read_text(encoding='utf-8')); print('YAML OK')"
git diff --check
python3 /home/l4nd0/tenn-agent-contract-registry-main-v1-20260607/scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md --repo-root .
git push -u origin safe/sloppy-fix-provider-failclosed-v1-20260607
```

Next command sequence, only after explicit merge/proof approval:

```bash
cd /home/l4nd0/tenn-sloppy-fix-provider-failclosed-v1-20260607
gh pr view 321 --json number,state,mergeStateStatus,statusCheckRollup,headRefName,baseRefName,url
gh pr merge 321 --merge
gh pr view 307 --json number,state,headRefName,statusCheckRollup,url
# Then rerun/trigger Sloppy Scan for PR #307, capture the downstream Sloppy Fix run ID,
# and verify the Sloppy Fix run fails closed for 3 seeded findings and 0 fixes.
```

## Blocked Items And DATA_MISSING

- Live Sloppy Fix run using the candidate fail-closed workflow:
  `DATA_MISSING`.
- Whether the live result is a deliberate failed status for 3 seeded/0 fixed:
  `DATA_MISSING`.
- Merge/land decision for PR #321: `DATA_MISSING`.
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
- Branch push: passed.
- PR #321 creation: passed.
- PR #321 Sloppy Scan: passed with zero issues.
- PR #321 downstream Sloppy Fix: passed, but only skip-success for zero issues;
  it did not prove the seeded-positive fail-closed gate.
- PR #307 patched live proof: `DATA_MISSING`.

## Raw Logs

- Raw logs were not persisted under `reports/`; the relevant log lines are
  summarized above. The downloaded proof artifact copy is under `/tmp` and may
  be ephemeral.

## Unsafe Actions Avoided

- No workflow dispatch/rerun.
- No PR merge.
- No PR #307 mutation.
- No issue mutation.
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
- PR #321 proves the pushed branch can run Sloppy Scan and downstream Sloppy
  Fix, but because the scan had zero findings and `workflow_run` uses the
  default-branch workflow definition, it does not prove the zero-fix fail-closed
  gate.

## Next Recommended Prompt

`Approved: merge PR #321 to main, then rerun one bounded Sloppy proof against PR #307 and verify the downstream Sloppy Fix fails closed; do not merge PR #307.`
