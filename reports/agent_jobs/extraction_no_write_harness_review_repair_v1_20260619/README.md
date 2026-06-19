# No-Write Harness Review Repair

State: DONE_WITH_RISK

Repaired the two PR #379 code-review findings:

- Secret-bearing env values are redacted from safe-env report artifacts.
- Replay status now fails closed when any side-effect containment boolean fails.

The full six-case extraction replay was not rerun because this repair does not
change extraction behavior. Existing risk remains: WHC is still extraction-red
in the saved replay, and real docling replay is still `DATA_MISSING` until an
approved docling-capable repo/backend venv exists.

Validation:

- task-card validate: PASS
- focused unit tests: PASS, 17 tests
- `py_compile`: PASS
- docling no-write preflight: expected `DATA_MISSING`
- report secret scan: PASS
- `git diff --check`: PASS
- task-card `check-diff`: PASS
