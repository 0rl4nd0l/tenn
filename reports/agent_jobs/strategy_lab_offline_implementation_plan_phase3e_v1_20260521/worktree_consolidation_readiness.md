# Worktree Consolidation Readiness

## Decision

The Phase 2/2B/3A/3B/3C worktrees are not ready to treat as committed baseline
inputs. They are available and useful as candidate evidence, but their current
state requires a consolidation/save plan before any production-module task-card
drafting.

Recommended next step: `GO_PHASE3F_CONSOLIDATION_SAVE_PLAN_ONLY`.

## Readiness Table

| Worktree | Current state | Ready as committed baseline? | Required before implementation |
|---|---|---:|---|
| Phase 2 authoritative artifact schema | untracked task card, docs, schema, fixtures; ignored report bundle | No | decide whether to save/merge/archive the untracked schema bundle |
| Phase 2B helper candidate | untracked helper doc, code, test, fixtures; ignored reports/raw outputs | No | preserve as pending-review helper candidate or archive as superseded |
| Phase 3A mocked adapter design | staged additions | No | resolve staged work by an approved save/merge/archive task |
| Phase 3B reconciled mocked adapter tests | untracked docs/test; ignored report bundle and pycache | No | decide save/merge/archive; exclude generated pycache from evidence |
| Phase 3C offline mock transport | untracked docs/test; ignored report bundle and pycache | No | decide save/merge/archive; preserve Phase 3C contract if approved |
| Phase 3D contract review | report bundle present; task card remains untracked in current checkout | Partially | preserve or intentionally absorb the Phase 3D task card/report state |

## Consolidation Classification

Active candidate inputs:

- Phase 2 `strategy_lab_artifact_v1` schema and fixtures.
- Phase 3A adapter contract, policy, envelope, quarantine, and test-plan docs.
- Phase 3B mock test vectors and offline test file.
- Phase 3C mock transport contract, lifecycle, fixtures, and offline test file.

Report-only evidence:

- Phase 2 report bundle.
- Phase 3A report bundle.
- Phase 3B report bundle.
- Phase 3C report bundle.
- Phase 3D report bundle.

Pending-review helper candidate:

- Phase 2B `strategy_lab_sidecar_artifact_v1` helper document, module, tests,
  fixtures, raw payloads, and normalized `backtest_run` / `regime_breakdown`
  helper artifacts.

Archive-only or duplicate/superseded candidates:

- older `strategy_lab_quantdinger_framework_v1_20260520` report bundles visible
  under Phase 3B and Phase 3C report trees;
- generated `__pycache__` files in Phase 3B and Phase 3C test directories;
- any Phase 2B helper material that conflicts with the later Phase 2
  authoritative envelope or Phase 3C pre-envelope boundary.

DATA_MISSING:

- proof that Phase 2/2B/3A/3B/3C files have been committed, merged, or otherwise
  preserved into an authoritative baseline;
- approved destination for each candidate bundle;
- approved handling of ignored report outputs and generated pycache files.

## Readiness Result

The consolidation/readiness checkpoint blocks direct movement to
production-module task-card drafting.

The next safe phase should be a plan-only consolidation/save decision that
answers:

- which worktree files should be saved as authoritative Strategy Lab design,
  schema, tests, or report evidence;
- which helper files should remain pending-review candidate evidence;
- which duplicate, older, ignored, or generated files should be archived or
  excluded;
- whether any staged Phase 3A files should be committed, unstaged, or replaced
  under a separately approved task;
- how to preserve Phase 3D task-card/report state without absorbing unrelated
  dirty work.

No merge, cherry-pick, commit, copy, stage, clean, stash, reset, remove, or
unstage operation was performed in Phase 3E.
