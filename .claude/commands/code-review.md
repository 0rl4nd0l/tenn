# Code Review

Expert code review of recent changes. Run `git diff` and review for quality, security, and maintainability.

## Instructions

- Run `git diff` (staged and/or unstaged) as the primary artifact.
- Focus on modified files only.
- Checklist: clarity/readability, naming, duplication, error handling, no exposed secrets/API keys, input validation, test coverage, performance.
- Classify each finding: **critical** (must fix), **warning** (should fix), **suggestion** (consider).
- Include concrete fix examples for each finding; no vague advice.
- After providing the review, offer to invoke `/code-fix` to apply findings.

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
    "critical": [{"file": "", "location": "", "issue": "", "fix_example": ""}],
    "warnings": [{"file": "", "location": "", "issue": "", "fix_example": ""}],
    "suggestions": [{"file": "", "location": "", "issue": "", "fix_example": ""}]
  }
}
```

## Validation

Before returning: confirm all requirements addressed; verify no contradictions in findings; confirm JSON schema is exact and valid. If any check fails, revise and recheck.
