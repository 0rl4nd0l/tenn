# Issue #558 ASXFP 09-12 canonical reconstruction

## Identity and ownership

- Exact accepted input from Issue #557: `b0338cbd00bda257faf07e96292864a1f95ae34c`.
- Integration branch: `codex-x/20260812T062313Z-38b8b6f405-1613cb`.
- Named owner: Codex, issue #558.
- Scope: ASXFP Tickets 09-12 canonical reconstruction.
- Scope fingerprint: `f9543cb45f615d2f82a5537d392577eb740597e62e5ebb53b574cd9367d38b9c`.
- Authoritative worktree: `/home/l4nd0/.codex-x-profiles/tenn/runs/20260812T062313Z-38b8b6f405-1613cb/workspace/source`.
- The bound Git context exposed only this launcher-owned worktree. No competing ownership was found.

## Refreshed candidate evidence

| Ticket | PR | Head | Base | Live state | Checks refreshed 2026-08-12 |
| --- | --- | --- | --- | --- | --- |
| 09 | #535 | `ba0688af97cdcaaf9cf21a0dddc2c1ba5aca2a33` | Ticket 08 branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 10 | #536 | `c57698a2e852d74d84dbb30402a0d654515d6a44` | Ticket 09 branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 11 | #538 | `a456008b0c55726afb1b24080581a46f689a2f19` | Ticket 10 branch | open draft, clean | `lint-and-test`: success; `scan`: success |
| 12 | #539 | `935ee122c91e9d7651bc85738acc586006656412` | Ticket 11 branch | open draft, clean | `lint-and-test`: success; `scan`: success |

The four candidates form a verified linear ancestry chain from historical Ticket 08 head
`9db0cb9a58c0475447f5cde41242e99d0d8cdac2`. The reconstruction replayed only the
twenty evidence-bearing Ticket 09-12 commits onto the exact accepted Issue #557 head.
No merge or rebase was performed, and no unrelated PR #537 content was carried forward.

## Changed scope

- Ticket 09: immutable adjusted/underlying disclosure lane with explicit labels and
  reconciliation evidence, kept fail-closed and separate from canonical statutory facts.
- Ticket 10: evidence-backed immutable supersession edges and restatement-terminal
  precedence without arrival-order or activity substitution.
- Ticket 11: deterministic unresolved-observation review provenance, audited decisions,
  conflict-truthful promotion, and pipeline/API wiring.
- Ticket 12: bounded scanned-announcement diagnostics, recognition-confidence gates,
  authenticated page-local selection, and structured page/region/row/cell provenance.
- Historical task cards and closeout reports are retained only as recovery evidence.
  No protected document, PDF, corpus, runtime output, or generated evaluation artifact
  was added.

## Validation

- Ticket 09, 10, and 11 historical task cards validate successfully with only their
  declared legacy-v1 warnings. Ticket 12 was an exceptional code-and-synthetic-test
  repair candidate and contains no task card.
- Combined focused and highest available no-write selection: `486 passed` across
  `test_financial_observations.py`, `test_financial_observation_reviews.py`,
  `test_asx_appendix4c_parser.py`, `test_asx_extraction_contracts.py`,
  `test_docling_extract.py`, and `test_multipass_extraction.py`.
- The minimal disposable dependency environment used pytest, SQLAlchemy, Pydantic,
  python-dateutil, FastAPI/httpx, Celery, Beautiful Soup, Qdrant client, and PyMuPDF.
- Repository-pinned Ruff 0.15.6 with `ruff.toml` on all changed Python: passed.
- `python3 -m py_compile` on all changed Python: passed.
- `git diff --check`: passed.
- No extraction, OCR, model, database, migration, service, queue, cache, runtime/data,
  source-document, protected-data, or canonical-fact write was executed.

## Review and handoff

- Standards and Spec review run against exact Issue #557 input
  `b0338cbd00bda257faf07e96292864a1f95ae34c` after the candidate is frozen.
- Blocking review findings must be repaired and re-reviewed before acceptance.
- Accepted carry-forward identity: resolve the final Issue #558 commit on the integration
  branch. Its immutable SHA is reported in the session handoff because a tracked file
  cannot truthfully contain its own commit identity.
- Next ticket: #559 must start from that exact accepted SHA and refresh canonical and
  ownership evidence before extending the stack.
- Recovery pointers: Issue #557 accepted SHA and PRs #535, #536, #538, and #539 with
  the four exact historical heads above.
- No merge, push, PR/issue mutation, deployment, runtime/data mutation, cleanup,
  branch/worktree deletion, closure, or registry release occurred.
