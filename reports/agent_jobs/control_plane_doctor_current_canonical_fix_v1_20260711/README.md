# Control Plane Doctor Current-Canonical Review Fix

## Objective

Retarget preserved doctor commit `231b4626` onto current canonical `21b7f6df`
and close the read-only publication-review findings without widening into
control-plane remediation.

## Current State

`DONE_WITH_RISK`

The current-canonical port, review fixes, validation, and skeptical review are
complete. A local commit is the bounded closeout outcome; publication remains
unauthorized.

## Evidence Used

- Remote canonical verified by `git ls-remote` as `21b7f6df` before worktree
  creation.
- Fresh worktree full Git Guard: `pass`, `VALID_TASK_WORKTREE`, registry and
  ledger `PASS`, no matching active work.
- Source worktree remained clean at exact commit `231b4626`.
- PR #478 remains open and isolated to `AGENTS.md`, `tenn-fix`,
  `tenn-git-guard`, and `CODEX_OPERATOR_GUIDE.md`; none was touched.
- No existing control-plane doctor PR was found.

## Changes

- Ported the exact doctor script, test, and focused documentation files from
  `231b4626`; SHA-256 values matched before review fixes.
- Added a read-only `git ls-remote` verification of the configured
  remote-tracking canonical ref.
- A stale cached ref now returns `WARN`; unavailable remote truth returns
  `DATA_MISSING`; neither can produce parity `PASS`.
- Added full public CLI fixtures for healthy exit `0`, stale-remote warning exit
  `1`, and unresolvable-canonical hard error exit `2`.
- Added `scripts/test_control_plane_doctor.py` as a focused current-CI pytest
  step.
- Updated the doctor operator document for remote-truth and CI semantics.

## Files Touched

- `.github/workflows/ci.yml`
- `docs/agent_tasks/control_plane_doctor_current_canonical_fix_v1_20260711.md`
- `docs/dev_flow/CONTROL_PLANE_DOCTOR.md`
- `scripts/control_plane_doctor.py`
- `scripts/test_control_plane_doctor.py`
- Five report artifacts in this directory

## Files Intentionally Not Touched

- Every PR #478 path.
- The preserved source worktree and commit.
- Host config/skills/hooks, systemd, deployed worktree, automation runner,
  runtime, data, extraction, ledger, registry, and GitHub.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Deterministic JSON that cannot claim canonical/deployed parity from a stale or unverified cached remote-tracking ref. |
| live output location | Command stdout from `scripts/control_plane_doctor.py`; no persistent doctor output is written. |
| pre-run max timestamp or count | Previous implementation emitted one JSON document but did not verify its cached canonical ref against remote truth. |
| post-run max timestamp or count | Real command emitted one parsed JSON document with eight checks and `canonical_ref_fresh=true`; remote and cached canonical both equal `21b7f6df`. |
| rows/files inserted or updated after run start | `0` runtime/data rows or output files; only exact task-card repo/report files changed. |
| readiness/gate status | Eight unittest and eight focused pytest cases pass; public CLI fixtures cover exits `0`, `1`, and `2`; task-card and diff gates pending final rerun. |
| exact command/query used | `python3 scripts/control_plane_doctor.py --repo-root . --json`; `python3 -m unittest -q scripts.test_control_plane_doctor`; ephemeral `uvx --from pytest pytest -c pytest.ini scripts/test_control_plane_doctor.py -q`; `git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1`. |
| result | `WORKING` |
| remaining blocker | `none` for remote-freshness grading and doctor JSON behavior; control-plane findings remain separate owner-gated remediation. |

result: WORKING

## Constraints And Unsafe Actions Avoided

- No push, PR, merge, rebase, or source-worktree modification.
- No host, systemd, deployed, runtime, data, extraction, ledger, registry, or
  GitHub mutation.
- No doctor finding was repaired.

## Remaining Risk

- Remote verification depends on network/auth availability and deliberately
  degrades to `DATA_MISSING` rather than trusting cache.
- Pytest passed under an ephemeral Python 3.13 environment with one unrelated
  unknown pytest-config-option warning; unittest passed under repo Python.
- Publication remains a separate approval boundary.
- A remote query timeout fails closed as command exit `2`; it does not produce
  parity success, but operators may distinguish timeout from other remote
  errors more finely in a future compatible revision.

## Next Recommended Prompt

See `NEXT_GOAL.md`.
