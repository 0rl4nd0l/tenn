---
name: tenn-code-reviewer
description: Tenn wrapper around the existing host code-reviewer skill. Read-only final diff or PR review gate focused on task-card scope, validation evidence, and Tenn product/runtime boundaries.
---

# Tenn Code Reviewer

Use `tenn-code-reviewer` as the final diff or PR review gate before push, PR,
merge, closeout, or owner-ready claims.

This wraps the existing host `code-reviewer` stance. It is read-only by
default.

## Preflight

Run `tenn-git-guard` and inspect:

- branch, HEAD, base, upstream, and dirty state
- task card and `allowed_files`
- diff scope
- validation evidence
- report bundle
- product/runtime/data/extraction boundaries
- GitHub PR metadata when reviewing a PR

## Review Focus

Lead with findings ordered by severity. Check:

- behavior regressions
- missing or weak validation
- disallowed path changes
- task-card mismatch
- owner approval gaps
- product/runtime/data/extraction boundary crossings
- unreported worker dirt
- stale branch or PR assumptions

## Output

Write `PR_REVIEW.md` when durable evidence is needed. The review decision should
be one of:

- `pass`
- `pass_with_risk`
- `revise`
- `block`

Do not fix code from this skill unless the owner explicitly switches into a
bounded `tenn-fix` execution flow.
