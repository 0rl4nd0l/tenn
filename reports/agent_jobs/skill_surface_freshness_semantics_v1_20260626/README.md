# Skill Surface Freshness Semantics

state: PR_READY
completed_at: 2026-06-26T05:33:12Z
worktree: /home/l4nd0/tenn-skill-surface-freshness-semantics-v1-20260626
branch: control-plane/skill-surface-freshness-semantics-v1-20260626
base: origin/migration/clean-runtime-baseline-reconstruct-v1
base_head: c877da6eb114826365339379f10a8a06e82221a5

## Objective

Stop `docs/dev_flow/SKILLS_SURFACE.md` from creating a self-invalidating
metadata loop where `last_verified_commit` must equal the latest canonical merge
commit after every docs PR.

## Result

DONE_WITH_RISK. The control-plane docs semantics are fixed and ready for a draft
PR. Runtime functionality is not in scope and was not proven.

Changed:

- Added `freshness_model: ancestor_plus_behavior_stale_files`.
- Added `freshness_checked_at` and `freshness_checked_against`.
- Clarified that `last_verified_commit` is the audited source commit for the
  skill-surface snapshot, not a value to churn after every metadata PR merge.
- Clarified that metadata-only freshness refreshes do not invalidate the
  audited skill surface.
- Kept the visible repo-backed skill count unchanged at 12.
- Kept legacy `.codex/skills` absent-directory-safe.

## Evidence

- Portable git guard: pass.
- Repo-backed git guard: pass.
- Registry read-only: pass, no active jobs.
- Task ledger validate: pass, 32 entries after the claimed ledger append.
- Task card validate: pass.
- Skill count: 12 `.agents/skills/**/SKILL.md` files.
- Legacy `.codex/skills` count: 0.
- Ancestor proof: `b3b3a154590f36e61d297c1ac79fe623526f0b28` is an ancestor of
  current canonical `c877da6eb114826365339379f10a8a06e82221a5`.
- Focused control-plane test: `tests/test_agent_task_ledger.py` 24 passed, 1
  existing pytest config warning.
- `git diff --check`: pass.

## Boundaries

No product, runtime, backend, extraction, parser, prompt, gold-label, evaluator,
schema, migration, service, model, GPU, DB, Qdrant, Redis, news, memory,
source-document, production-data, host-global, branch-history, merge, rebase,
reset, stash, prune, delete, or cleanup action was performed.

## Remaining Risk

Host picker/autocomplete visibility remains `DATA_MISSING`; this lane only
validates repo-visible skill-surface semantics.

## Next Action

Push the branch and open the approved draft PR against
`migration/clean-runtime-baseline-reconstruct-v1`.
