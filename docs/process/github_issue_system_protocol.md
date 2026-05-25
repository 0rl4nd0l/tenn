# Tenn GitHub Issue System Protocol

## Summary

GitHub Issues are Tenn's live actionable backlog. Reports, task cards, memory,
and merge parking support the backlog, but they must not become disconnected
places where real bugs and follow-ups disappear.

## Source Roles

- GitHub Issues: live actionable backlog for confirmed bugs, gaps, trust risks,
  follow-ups, blockers, and work that needs a task card.
- Milestones: execution batches that group issues by current operating focus.
- Projects: dashboard and view layer for filtering, prioritizing, and tracking
  issue state across lanes.
- Task cards: execution contracts that define allowed files, surfaces, mode,
  validation, hard stops, and whether GitHub mutation is approved.
- Reports: evidence artifacts, matrices, validation output, and closeout proof.
- Project Memory: durable coordination memory and search hints, not current
  truth and not a substitute for GitHub issue tracking.
- Merge parking: completed-but-unmerged review queue. Parking is not merge
  approval and is not a closed issue unless the parked item is linked.

## Label Policy

Issue skills should recommend these labels and apply them only when the current
task card or user instruction explicitly permits GitHub mutation:

- `lane:*`: primary ownership lane.
- `mode:*`: audit, safe-extension, implementation, result-review, or closeout.
- `priority:*`: P0, P1, P2, or P3 urgency.
- `risk:*`: low, medium, high, or boundary-sensitive risk.
- `state:*`: ready, blocked, parked, needs-review, duplicate, superseded, or done.
- `type:*`: bug, gap, trust-risk, seed-regression, usability, repo-control,
  runtime, follow-up, audit, or docs.

Recommended labels must be included in issue drafts even when live label
application is not approved.

## Milestone Policy

Recommend one milestone when the issue naturally belongs to an execution batch:

- `M0 Control Plane Hardening`
- `M1 Trust / Provenance Foundation`
- `M2 Evaluation Spine`
- `M3 Query + Memory Integrity`
- `M4 Financial Truth Expansion`
- `M5 Cockpit Analyst Workflow`
- `M6 Runtime / Local Automation`

Do not invent milestones during validation. If the milestone does not exist or
GitHub mutation is not approved, record it as a recommendation only.

## Project Policy

When Projects are available, recommend field values rather than relying on
labels alone:

- Lane
- Mode
- Risk
- Priority
- Status
- Task Card
- Report Path
- Blocked By
- Root Cause Fixed
- Follow-up Required
- Production Data Access

If Project access or schema is missing, record `DATA_MISSING` and keep the issue
body complete enough to backfill the Project later.

## PR Link Policy

- Use `fixes #X` only when product remediation actually landed, validation
  passed, and the issue should auto-close on merge.
- Use `refs #X`, `audit for #X`, or normal references for audit-only,
  report-only, partial, parked, exploratory, or follow-up work.
- Never let an audit-only PR auto-close a remediation issue.
- If a PR is only evidence, report generation, or issue triage, keep the issue
  open unless every unresolved actionable item is tracked elsewhere.

## Audit Closeout Rule

An audit issue can close only if every unresolved actionable finding is one of:

- linked to an existing GitHub issue or PR;
- converted into a new GitHub issue when approved;
- parked for merge or review with a visible parking link;
- marked `NO_FOLLOWUP` with a reason; or
- marked `DATA_MISSING` with the exact evidence needed.

Otherwise leave the issue open with a blocker or status comment.

## Follow-Up Issue Rule

For `FOLLOWUP_REQUIRED` findings, issue-finder and closeout skills must create
or link a GitHub issue when explicitly approved. Each follow-up issue must
include:

- `## Summary` in plain language.
- Lane and supporting lanes.
- Mode.
- Recommended labels.
- Recommended milestone.
- Optional Project field values.
- Task-card path.
- Report path.
- Allowed and forbidden surfaces.
- Validation plan.
- Hard stops.
- Definition of done.

## De-Duplication Rule

Before creating any issue, search:

- open issues;
- closed issues;
- open and closed PRs;
- recent reports and task cards; and
- merge parking entries.

Do not duplicate an issue when an existing tracker covers the same root cause,
lane, validation path, and hard stops. Similar symptoms alone are not enough to
declare a duplicate.

## Automation Alignment

Automated reports should do one of these:

- create issue-ready findings;
- draft issue-ready findings when GitHub mutation is not approved;
- update existing issue references when approved; or
- mark low-value or unsupported items as `DEFER` or `NO_FOLLOWUP`.

Do not maintain disconnected bug, opportunity, or remediation registries that
never reach GitHub Issues, a linked PR, a task card, or a merge-parking entry.

## Closeout Matrix

Closeout and discovery reports should preserve a compact matrix:

| Issue/Finding | Lane | Labels | Milestone | Project Fields | Tracker | Follow-up Required | DATA_MISSING | Next Action |
| ------------- | ---- | ------ | --------- | -------------- | ------- | ------------------ | ------------ | ----------- |

This matrix is the handoff source for fresh Codex/GPT continuations.
