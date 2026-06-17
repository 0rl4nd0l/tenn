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
- Docs Impact Check fields
- model/subagent routing fields
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
- whether the diff is the smallest readable, testable change that solves the
  task
- unnecessary new abstraction or opportunistic unrelated refactor
- whether tests/checks actually ran or are honestly marked unavailable
- unfilled templates that imply approval, success, or evidence that was not
  provided
- missing or dishonest Docs Impact Check fields:
  - `docs_impact`
  - `docs_checked`
  - `docs_changed`
  - `docs_followup`
  - `reason`
- undocumented behavior, schema, command usage, workflow, validation, operator
  step, artifact shape, API, data model, skill trigger, or safety-boundary
  changes
- model/subagent routing fields:
  - `task_tier`
  - `recommended_model`
  - `actual_model`
  - `why_this_model`
  - `worker_model_allowed`
  - `worker_decision_limit`
  - `escalation_needed`
- whether small/cheap workers made decisions above their allowed risk tier
- counter-lineage evidence when the diff changes metric, evaluation, daemon
  status, score, pass-rate, or count reporting

## Docs Impact Gate

Do not pass a PR or owner-ready closeout with undocumented behavior changes.
If docs were not needed, the diff must record `DOCS_NOT_REQUIRED` and a reason.
If docs should change but cannot be updated in scope, require `DOCS_FOLLOWUP`
with a concrete issue, report, or task-card path.

For durable docs, templates, and skills, check whether freshness metadata is
present when useful: `last_verified_commit`, `last_verified_pr`,
`source_of_truth_files`, `stale_if_files`, `owner`, and `evidence_grade`.

## Model Routing Gate

Review routing as Codex development-tooling policy, not Tenn runtime behavior.
Use Tenn-specific escalation only when the diff depends on this repo's
task-card registry, owner-boundary rules, extraction boundaries, or
financial-truth safety constraints.

Expected tiers:

- `small`: bounded evidence gathering and simple docs/test tasks; mini/low-cost
  is acceptable.
- `medium`: one/two-file implementation; standard coding model is acceptable.
- `large`: architecture, schema, persistence, or tricky debugging; high
  reasoning is expected.
- `critical`: DB/runtime mutation, destructive Git, financial truth, merge
  conflict, high-risk cleanup, or owner-boundary decision; high reasoning plus
  review-board is expected.

## Output

Write `PR_REVIEW.md` when durable evidence is needed. The review decision should
be one of:

- `pass`
- `pass_with_risk`
- `revise`
- `block`

Do not fix code from this skill unless the owner explicitly switches into a
bounded `tenn-fix` execution flow.
