# No-Write Harness P2 Review Repair

State: DONE

Adopted and validated the overlapping PR #379 P2 repair packet that was present
after the git-status audit commit.

Change summary:

- Validates the certified manifest and selected cases before report outputs are
  reset, preserving stale reports when selector validation fails.
- Validates the loopback LLM URL before report outputs are reset, preserving
  stale reports when URL validation fails.
- Changes certified guard-case source paths from host-specific absolute paths to
  portable `asx/docs/...` paths.
- Resolves relative source paths against `DATA_ROOT`, repo-local data, and the
  existing shared Tenn data root without fetching or creating source files.
- Adds focused tests for invalid-selector and invalid-LLM-URL report
  preservation plus portable source-path resolution.
- Runs a preflight-only no-write replay to prove the portable paths resolve on
  this host.

Validation:

- task-card validate: PASS
- focused unit tests: PASS, 28 tests
- `py_compile`: PASS
- JSON parse for manifest and report artifacts: PASS
- preflight-only no-write replay: PASS, 6 cases, side_effect_pass=true
- `git diff --check`: PASS
- task-card `check-diff`: PASS
- report artifact check: PASS
- repeat read-only review: PASS

Docs Impact Check:

- docs_impact: DOCS_UPDATED
- docs_checked:
  - docs/agent_tasks/extraction_no_write_harness_review_p2_repair_v1_20260619.md
- docs_changed:
  - docs/agent_tasks/extraction_no_write_harness_review_p2_repair_v1_20260619.md
- docs_followup: NONE
- reason: task card documents the portable manifest paths and pre-clear
  validation behavior.

Task Ledger:

- live registry preflight: active_jobs empty
- committed ledger: DATA_MISSING on this branch
- ledger update: DATA_MISSING because `scripts/agent_task_ledger.py` is not
  present on this PR branch

Residual facts unchanged:

- The full extraction replay was not rerun for this repair.
- WHC remains extraction-red in the saved no-write replay.
- Docling-backed replay remains `DATA_MISSING` until an approved venv exists.
