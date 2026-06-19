# PR #379 Follow-Up Safety Review

Decision: pass, pending push and fresh GitHub checks.

## Findings

No blocking findings in the focused no-write harness safety diff.

## Review Coverage

- Already-dirty repo files are now content-snapshotted before replay and
  compared after replay; a mutation to an already-dirty file fails
  `repo_worktree_write` and `side_effect_pass`.
- Normal parser cache snapshots now cover the whole cache root and include file
  hashes, so unpredicted ignored cache files are detected.
- `docling-no-write` now preserves read-only source-root `DATA_ROOT` and
  `DOCS_ROOT` during re-exec, then still applies isolated runtime roots before
  replay.
- `docling-no-write` forces selected cases to strict docling semantics, so the
  profile cannot pass through PyMuPDF fallback.
- Unexpected per-case extraction exceptions now produce `FAIL`, not
  `DATA_MISSING`.

## Validation

- Task-card validate: PASS
- Unit tests: PASS, 26 tests
- `py_compile`: PASS
- `git diff --check`: PASS
- Task-card `check-diff`: PASS
- Report artifact check: PASS
- Baseline certified no-write preflight: PASS

## Residual Facts

- Full extraction replay was not rerun for this follow-up.
- PR #379 CI/review state still needs a fresh GitHub read after push.
- WHC exact-case period/source proof from the worker is not integrated here.
