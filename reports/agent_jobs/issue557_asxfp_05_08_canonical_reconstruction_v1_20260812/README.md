# Issue #557 ASXFP 05-08 canonical reconstruction

## Identity and ownership

- Canonical authority refreshed 2026-08-12: `migration/clean-runtime-baseline-reconstruct-v1` at `38b8b6f4056de46fbdb70a116eee7e1bd4556352`.
- Integration branch: `codex-x/20260812T062313Z-38b8b6f405-1613cb`.
- Named owner: Codex, issue #557.
- Scope: ASXFP Tickets 05-08 canonical reconstruction.
- Scope fingerprint: `7da03982a41d04802c9c4b447651ffe07b41701e29a2b3b2e4bd08f1013db119`.
- Authoritative worktree: `/home/l4nd0/.codex-x-profiles/tenn/runs/20260812T062313Z-38b8b6f405-1613cb/workspace/source`.
- `git worktree list --porcelain` exposed only this launcher-owned integration worktree in the bound Git context. No competing ownership was found.

## Refreshed candidate evidence

| Ticket | PR | Head | Base | Live state | Checks refreshed 2026-08-12 |
| --- | --- | --- | --- | --- | --- |
| 05 | #531 | `84295111c6ae400de4e6f1c6cd941a45a0f549a3` | canonical migration branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 06 | #532 | `f063c2a4cb4b9c677f35498de4b80f31dba55ba6` | Ticket 05 branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 07 | #533 | `dc4e99e305218dfea072e9c78cb13476dc6899fe` | Ticket 06 branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 08 | #534 | `9db0cb9a58c0475447f5cde41242e99d0d8cdac2` | Ticket 07 branch | open draft, clean | `lint-and-test`: success; `scan`: success |

All four candidates descend in order from historical canonical `b01885d6cd55242339662e91d18141aeb725f089`. Live canonical has one later commit, `38b8b6f4`, whose runtime-router files do not overlap the Ticket 05-08 delta. The reconstruction replayed the twelve evidence-bearing Ticket 05-08 commits without merge or rebase; no unrelated candidate-branch changes were carried forward.

## Changed scope

- Ticket 05: immutable, deterministic source-context observation identity; fail-closed, atomic staging; additive API/pipeline wiring; migration and ORM contract.
- Ticket 06: closed ten-metric statutory projection with unit/currency/source evidence and no expansion of persistence authority.
- Ticket 07: source-bound `period_only` and `year_to_date` identities, conflict abstention, and additive compatibility reads.
- Ticket 08: isolated Appendix 4C cash profiles with authenticated row/cell evidence, constrained fallback, deterministic conflict handling, and ambiguity abstention.
- Historical ticket contracts and closeout reports are retained as recovery pointers. No PDF, protected corpus, runtime output, or generated evaluation artifact was added.

## Validation

- Four historical task cards validate successfully with only their declared legacy-v1 warnings.
- `test_financial_observations.py`: 46 passed.
- `test_asx_appendix4c_parser.py`: 28 passed.
- `test_asx_extraction_contracts.py`: 9 passed.
- `test_multipass_extraction.py`: 302 passed at the highest available production-shaped no-write seam after installing the repository-pinned PyMuPDF and HTTP/Qdrant client dependencies in a throwaway environment.
- Combined current focused and no-write integration selection: 385 passed.
- The complete CI pytest scope was invoked once. Collection stopped with 68 environment errors because the disk-constrained minimal environment lacks unrelated FastAPI, Celery, YAML, and other full-stack dependencies; no test body failed. The higher ASXFP no-write seam above collected fully and passed.
- Ruff on all changed Python: passed.
- `python3 -m py_compile` on all changed Python: passed.
- `git diff --check`: passed.
- No migration, database, service, model, queue, cache, source-document, protected-data, or canonical-fact write was executed.

## Review

- Initial Standards review found three blockers: ambiguous Appendix denomination evidence, a quarterly legacy-input bypass, and an ORM random-ID default. All were repaired and covered at public seams. Its two non-blocking duplication/data-clump observations are retained for later refactoring rather than widening this recovery lane.
- Initial Spec review found conflicting authenticated fallback selection, stale broad active-goal material, and missing current lane evidence. Fallback conflicts now abstain, the four misleading active-goal files are excluded, and this report supplies the current exact identity/evidence envelope.
- Final exact-head Standards and Spec reviews are summarized in the session handoff.

The initial environment lacked pytest. A throwaway virtual environment was built under `/tmp`. The full CUDA dependency set could not be installed because the host had less than 1 GiB free; the supported CPU-wheel attempt also exhausted space. Focused and production-shaped no-write tests therefore used a minimal dependency environment. The exact two-axis review result is recorded in the final session handoff after it runs against the frozen candidate.

## Recovery and handoff

- Exact canonical base: `38b8b6f4056de46fbdb70a116eee7e1bd4556352`.
- Historical recovery pointers: PRs #531, #532, #533, and #534 and the four exact heads in the table above.
- Candidate/accepted carry-forward identity: resolve the final issue #557 commit on `codex-x/20260812T062313Z-38b8b6f405-1613cb`; the immutable SHA is reported in the session handoff because a tracked file cannot truthfully contain its own commit identity.
- Next ticket: #558 must start from that exact accepted SHA and refresh canonical/ownership evidence before extending the stack through Tickets 09-12.
- No merge, push, PR/issue mutation, deployment, runtime/data mutation, cleanup, branch/worktree deletion, or registry release occurred.
