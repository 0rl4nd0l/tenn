---
name: code-reviewer
description: Review the current git diff or modified files for bugs, risks, regressions, maintainability issues, and missing tests. Use when the user asks for a review or wants findings before fixing code.
---

# Code Reviewer

Use this skill for review-only passes over current changes.

## Workflow

1. Run `git diff` for staged and unstaged changes.
2. Focus on modified files only.
3. Check for:
   - correctness and regressions
   - error handling
   - secrets exposure
   - input validation
   - performance issues
   - missing or weak tests
   - readability and duplication
4. Classify each finding:
   - `critical`
   - `warning`
   - `suggestion`
5. Provide a concrete fix example for every finding.

## Output

Produce structured findings with:

- `status`
- `work_log`
- `result.critical`
- `result.warnings`
- `result.suggestions`

Each finding must include:

- `file`
- `location`
- `issue`
- `fix_example`

Default user-facing output should be normal prose with findings ordered by severity. Only emit raw JSON if the user explicitly asks for JSON.

## Constraints

- Review only. Do not edit files while using this skill.
- Prioritize real defects and behavioral risk over style chatter.
