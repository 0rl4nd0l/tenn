# Code Fix

Applies code review or function-quality findings with minimal, targeted edits.

## Instructions

- Input comes from `/code-review` or `/function-quality` output (critical / warnings / suggestions with file, location, issue, fix_example).
- Apply fixes in order: **critical first**, then warnings, then suggestions.
- If `implementation_notes` are present (e.g. from `/function-quality`), follow them.
- One logical change per fix where possible; match existing style and patterns; do not introduce new issues.
- Add or update tests if the review flagged missing coverage.
- Populate work_log: assumptions, sources_used, files_read, files_modified, validation_checks.
- After edits, suggest running the relevant test suite.

## Output Format

```json
{
  "status": "SUCCESS | DATA_MISSING | ERROR",
  "work_log": {
    "assumptions": [],
    "sources_used": [],
    "files_read": [],
    "files_modified": [],
    "validation_checks": []
  },
  "result": {
    "changes_summary": [],
    "deferred": [],
    "test_suggestion": ""
  }
}
```

## Validation

Before returning: confirm all required fixes addressed or explicitly deferred; verify no new issues introduced; confirm JSON schema is exact and valid. If any check fails, revise and recheck.
