# Decisions

## Remote Truth

- Keep the configured canonical ref as the local comparison surface.
- Derive its configured remote and branch, then use read-only `git ls-remote`
  for current truth.
- Return `WARN` when cache differs from remote and `DATA_MISSING` when remote
  truth is unavailable. Only verified agreement can pass.
- Do not fetch or mutate remote-tracking refs.

## Tests And CI

- Exercise the public CLI—not only helper functions—for all three exit classes.
- Preserve the whole-run no-write snapshot assertion in the healthy CLI test.
- Add one focused pytest step to current canonical CI after the existing event
  waiter step rather than introducing another workflow.

## Code Fixer Result

```json
{
  "status": "SUCCESS",
  "work_log": {
    "assumptions": [
      "The configured canonical ref is a Git remote-tracking ref for normal operator use.",
      "Remote unavailability must never be treated as parity success."
    ],
    "sources_used": [
      "read-only review findings for commit 231b4626",
      "current canonical CI at 21b7f6df",
      "existing doctor script, tests, docs, and task contract"
    ],
    "files_read": [
      "scripts/control_plane_doctor.py",
      "scripts/test_control_plane_doctor.py",
      "docs/dev_flow/CONTROL_PLANE_DOCTOR.md",
      ".github/workflows/ci.yml"
    ],
    "files_modified": [
      "scripts/control_plane_doctor.py",
      "scripts/test_control_plane_doctor.py",
      "docs/dev_flow/CONTROL_PLANE_DOCTOR.md",
      ".github/workflows/ci.yml"
    ],
    "validation_checks": [
      "RED and GREEN stale cached canonical CLI fixture",
      "hard-error CLI fixture",
      "healthy verified-remote CLI fixture",
      "unittest and focused pytest"
    ]
  },
  "result": {
    "changes_summary": [
      "Added remote canonical verification and explicit freshness grading.",
      "Added full public CLI 0/1/2 fixtures.",
      "Added focused current-CI coverage and updated operator documentation."
    ],
    "deferred": [],
    "test_suggestion": "Run unittest, focused pytest, the real doctor command, and final task-card/guard gates."
  }
}
```

## Owner Boundaries

No publication, remediation, host/live, product, runtime, data, extraction,
ledger, or registry action is authorized by this task.

## Skeptical Code Review

```json
{
  "status": "SUCCESS",
  "work_log": {
    "assumptions": [
      "Remote unavailability must fail closed and must not be treated as canonical parity.",
      "The CI environment installs pytest before the focused doctor step."
    ],
    "sources_used": [
      "full current worktree diff",
      "source commit 231b4626",
      "current canonical 21b7f6df",
      "task-card validation and real doctor output"
    ],
    "files_read": [
      "scripts/control_plane_doctor.py",
      "scripts/test_control_plane_doctor.py",
      "docs/dev_flow/CONTROL_PLANE_DOCTOR.md",
      ".github/workflows/ci.yml",
      "docs/agent_tasks/control_plane_doctor_current_canonical_fix_v1_20260711.md"
    ],
    "files_modified": [],
    "validation_checks": [
      "clarity and naming",
      "remote input and error handling",
      "secret exposure",
      "read-only behavior",
      "CLI and CI test coverage",
      "performance and timeout behavior"
    ]
  },
  "result": {
    "critical": [],
    "warnings": [],
    "suggestions": [
      {
        "file": "scripts/control_plane_doctor.py",
        "location": "remote_canonical_sha",
        "issue": "A git ls-remote timeout currently reaches the top-level fail-closed exit 2 path rather than a check-local DATA_MISSING result.",
        "fix_example": "If operators need finer classification later, catch subprocess.TimeoutExpired inside remote_canonical_sha and return a timeout-specific remote_canonical_error while preserving non-PASS status."
      }
    ]
  }
}
```
