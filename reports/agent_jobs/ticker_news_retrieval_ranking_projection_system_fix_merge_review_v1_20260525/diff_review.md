# Diff Review

## Scope

Reviewed parked commit `9bfd0a6afabcafbfee7d061bbca11ba55b2cdbf1` against
canonical `9326c200ff187032b934ff9a33bf53e8a6f96181`.

## Findings

No blocking findings.

- Changed files are within the merge-review task-card scope.
- Canonical drift since `173a8750caa4602e5791ee072673db17e708c5d3` did not
  modify `rag.py`, `cockpit_api.py`, or the focused backend tests.
- `git merge-tree` reported a clean merge result.
- `git cherry-pick -x` completed without conflicts as `d0ec3243`.
- The diff changes backend-owned retrieval and source-pack behavior only.

## Architecture Review

- `SYSTEM_CONTRACT.md` §1.3 and §5 keep retrieval backend-owned. The change
  stays inside backend `rag.py` and backend route source-pack assembly.
- `SYSTEM_CONTRACT.md` §7 forbids parallel systems. The change extends the
  existing Qdrant news retrieval path and does not introduce another retrieval
  implementation.
- `SYSTEM_CONTRACT.md` §8 requires visible failure instead of masking. No-hit,
  context-only, data-insufficient, missing-required, and degraded rows remain
  unverified.
- `SYSTEM_CONTRACT.md` §10 forbids bypassing backend and forbidden fallbacks.
  The change does not add cockpit-side Qdrant access or DB access.

## Guard Review

`financial-engine_v2/backend/app/services/chat_evidence_guard.py` was not
changed. The route change only marks successful local-news hits as
`claim_verified` plus `local_news_context`; degraded/no-hit/context-only cases
continue through the guard as unverified evidence gaps.

## Residual Risks

- `NST` still has a residual relevance-quality risk where a broad linked
  resources article can rank above older primary NST evidence.
- Canonical SQLite news projection remains absent by design and was not repaired.
- Live endpoint behavior still requires backend serving-code smoke after
  canonical is updated.
