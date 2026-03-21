---
name: code-fixer
description: Apply findings from code-reviewer or function-quality with minimal targeted edits, fixing critical issues first and adding tests when required.
---

# Code Fixer

Use this skill when you already have structured findings and need to implement them.

## Expected Input

Structured findings with:

- `critical`
- `warnings`
- `suggestions`

Each item should include `file`, `location`, `issue`, and `fix_example`.

## Workflow

1. Apply fixes in order:
   - critical
   - warnings
   - suggestions
2. Keep each change minimal and aligned with existing patterns.
3. Add or update tests when the findings indicate missing coverage.
4. Record what was changed and what was deferred.
5. Suggest the relevant validation command set after edits.

## Output

Track structured implementation notes with:

- `status`
- `work_log`
- `result.changes_summary`
- `result.deferred`
- `result.test_suggestion`

Default user-facing output should be a normal prose summary of what changed, what was deferred, and how it was validated. Only emit raw JSON if the user explicitly asks for JSON.

## Constraints

- Do not invent fixes that are not supported by the findings.
- Explicitly defer anything not completed.
