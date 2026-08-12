# Issue #559 ASXFP Ticket 13 integration

## Identity and ownership

- Exact accepted input from Issue #558: `6432765591f458fb54849926295a647f5831fd0b`.
- Input tree: `12912f883cf974b9f7b8fe5323568c2c648bd613`.
- Integration branch: `codex-x/20260812T062313Z-38b8b6f405-1613cb`.
- Named owner: Codex, Issue #559.
- Scope: reproduce, classify, and integrate ASXFP Ticket 13 period/table/basis selection.
- Authoritative worktree: `/home/l4nd0/.codex-x-profiles/tenn/runs/20260812T062313Z-38b8b6f405-1613cb/workspace/source`.
- `git worktree list --porcelain` exposed only the launcher-owned worktree and no competing ownership.

## Refreshed authority and candidate

- Live Issue #559 was open and labelled `ready-for-agent`; it binds this work to the exact Issue #558 accepted head.
- PR #540 remained an open draft at historical candidate `16d3269c73f2ac45083e7da2101b1598836e63a5`, based on PR #539.
- PR #540 was mergeable but unstable: `scan` passed and `lint-and-test` failed.
- The candidate contained one Ticket 13 commit affecting only the financial-observation service, multipass extraction service, and their focused tests.
- The historical candidate was carried forward as a patch onto the exact Issue #558 head. No merge or rebase was performed.

## Diagnosed failure identity

The complete archived GitHub Actions log for job `90798594327` proves that Ruff,
installation, the Codex event-waiter tests, and scanning passed. The failing step was
`scripts/test_control_plane_doctor.py::ControlPlaneDoctorTests::test_cli_healthy_fixture_is_deterministic_and_read_only`:
two newly initialized synthetic Git repositories unexpectedly had different root-commit
SHAs. Backend and cockpit tests were skipped after that failure. This was CI/test-fixture
nondeterminism, not Ticket 13 product behavior. The same complete control-plane file now
passes locally (`8 passed`) without a Ticket 13 or control-plane change.

The deterministic Ticket 13 red loop instead exercised the public period-binding seam on
the exact accepted head. A production-shaped table with current-quarter and year-to-date
columns sharing `31 March 2025` failed because `_bind_current_period_column` did not accept
or preserve `period_basis`. Red commit: `285f0c62`.

## Repair and behavior

- Repair commit: `eecf1e60fc80ed701d824b2a3bd58d2afefe8c2d`.
- Equal top statement-table evidence now abstains instead of selecting by incidental order.
- Announcement-date metadata is excluded from financial-period binding.
- Same-date quarter-only and year-to-date columns require explicit basis evidence and bind only the requested basis.
- Conflicting or missing basis, ambiguous tables, ambiguous columns, and invalid period inputs remain fail closed.
- Bound quarter observations preserve table index, column index, column role, period basis, header evidence, and source-cell provenance.
- Financial-observation staging rejects quarter observations missing those explicit source-cell fields.
- The accepted Ticket 12 OCR selection and cell-provenance repairs remain in the ancestry and were not conflicted or replaced.

## Validation

- Red tracer: one expected `TypeError` before implementation because the accepted binding seam had no `period_basis` parameter.
- Focused period/table/provenance seam: `91 passed`.
- Complete highest available no-write ASXFP 05-13 seam: `498 passed` across financial observations, observation reviews, Appendix 4C parsing, ASX extraction contracts, Docling extraction, and multipass extraction.
- Historical failing control-plane file: `8 passed`.
- Repository-pinned Ruff 0.15.6 on all changed Python: passed.
- Python compilation on all changed Python: passed.
- `git diff 6432765591f458fb54849926295a647f5831fd0b...HEAD --check`: passed.
- No extraction, OCR, model, database, migration, service, queue, cache, runtime/data, source-document, protected-data, or canonical-fact write was executed.

## Review, recoverability, and handoff

- Standards and Spec review run against exact fixed point `6432765591f458fb54849926295a647f5831fd0b`; final findings are recorded in the session handoff.
- The red tracer and repair are separate commits, so the change is recoverable or revertible without reconstructing the historical stack.
- Accepted carry-forward identity is the final Issue #559 commit on this branch. Its immutable SHA is reported in the session handoff because a tracked file cannot truthfully contain its own commit identity.
- No push, merge, PR/issue mutation, deployment, runtime/data mutation, cleanup, branch/worktree deletion, closure, or registry release occurred.
