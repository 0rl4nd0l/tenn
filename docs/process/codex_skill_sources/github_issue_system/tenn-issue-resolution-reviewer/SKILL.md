---
name: tenn-issue-resolution-reviewer
description: Skeptical post-fix reviewer for Tenn issues, PRs, batches, and closeout reports. Use when Codex needs to decide whether a claimed Tenn issue resolution truly fixed root cause, preserved architecture and truth boundaries, avoided regressions across tickers, routes, docs, and workflows, and is safe to close, park, or keep open.
---

# Tenn Issue Resolution Reviewer

Review claimed Tenn issue resolutions before high-risk closeout. Treat the job as read-only unless the user explicitly invokes it through `tenn-issue-closeout` with a valid task card and all close gates pass.

## Core Rule

Do not accept "tests passed" or "audit complete" as proof that an issue is fixed. Require fresh repo, report, task-card, and GitHub evidence. Project Memory can guide search, but current repo/GitHub evidence is stronger than stale memory.

Never close issues, create comments, create issues, merge, park, or mutate product/runtime/data surfaces from this skill alone. If follow-up creation or issue closure is needed, hand the result to `tenn-issue-closeout` or require explicit user authorization and task-card permission.

## Supervisor Compatibility

Use this reviewer as a bounded quality gate inside a supervised closeout run. Review one issue, one PR, one report, or one compact batch matrix at a time; do not absorb the full accumulated sweep context.

If Codex supports actual subagents, use independent read-only reviewer subagents for root-cause, regression, security/boundary, financial-truth/provenance, user-value, skeptic/opposition, and final arbitration. If actual subagents are unavailable, emulate those reviewers as named passes with compact outputs.

Durable state lives in the issue matrix, reports, GitHub links, and parking entries. This skill should read those artifacts and return a compact verdict, not maintain a growing memory of earlier issues.

## Scope

Review any of these inputs:

- One GitHub issue.
- A batch of issues.
- A PR or branch that claims to resolve issues.
- A closeout report or audit report.
- A completed-but-unmerged branch proposed for parking.

Classify the lane before review: `Financial Truth`, `Evaluation`, `Provenance`, `Query Orchestration`, `Memory`, `Reporting`, `Cockpit / Usability`, `Repo Hygiene / Dev-agent`, `Performance / Local Runtime`, or `Security / Boundary`.

## Branch Hygiene / Merge Visibility Review

When reviewing a branch, PR, worktree, or closeout that depends on unmerged branch work, decide whether the work is merge-ready, should be parked, is blocked, is superseded, or needs a branch review issue. This review is read-only. Do not delete, prune, reset, stash, merge, rebase, or cherry-pick branches.

Assign one branch classification:

```text
ACTIVE_LINKED
PARKED_READY_FOR_REVIEW
PARKED_NEEDS_REBASE
BLOCKED_BY_CI
BLOCKED_BY_DEPENDENCY
SUPERSEDED
STALE_UNKNOWN_NEEDS_AUDIT
SAFE_TO_ARCHIVE_CANDIDATE
```

Review these branch dimensions:

- Merge readiness: base commit, branch HEAD, divergence, conflicts if already known, changed files, and linked PR state.
- Regression risk: blast radius across tickers, source types, routes, docs, workflows, tests, reports, and control-plane scripts.
- Validation: focused tests, report checks, CI status, `git diff --check`, and any unavailable evidence marked `DATA_MISSING`.
- Supersession: whether another branch, PR, issue, report, or commit covers the same objective and validation path.
- Parking eligibility: task card, report path, changed-file summary, validation evidence, blockers, and next review action are visible.
- Cleanup eligibility: `SAFE_TO_ARCHIVE_CANDIDATE` is only a non-destructive recommendation. Actual archive/delete/prune requires separate explicit approval.

Use `PARK_FOR_REVIEW` only when completed or frozen unmerged work has enough evidence for a visible parking path. Use `BLOCKED_DATA_MISSING` when unique commits, meaningful changed files, validation, PR state, or supersession evidence cannot be determined.

Recommended branch review issue tracking:

- Labels: `lane:repo-hygiene`, `type:control-plane`, `state:needs-review` / `state:parked` / `state:blocked` / `state:data-missing`, `risk:medium` or `risk:high`, and `mode:audit` or `mode:result-review`.
- Milestone: `M0 — Control Plane Hardening`.

## Hard Boundaries

Preserve Tenn architecture and orchestration rules:

- Task cards are permission contracts.
- Audit-only work is not product remediation.
- Repo and GitHub evidence outrank Project Memory.
- Seed regressions require root-cause and blast-radius analysis.
- Merge parking is for completed-but-unmerged work and is not merge approval.
- Do not mutate production DB, Qdrant, news, memory stores, canonical financial truth, parser routing, extraction prompts, gold labels, model/runtime/GPU/service config, CI control surfaces, or unrelated dirty files.
- Do not introduce hidden fallbacks, label relaxation, ticker-specific special cases, or broad rewrites to justify closeout.

## Evidence Pass

Gather only the evidence needed for the review:

```bash
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git diff --stat
git diff --check
git log --oneline --decorate -20
```

Use read-only GitHub and repo queries where relevant:

```bash
gh issue view <issue> --repo 0rl4nd0l/tenn --comments
gh pr view <pr> --repo 0rl4nd0l/tenn --comments --files
gh issue list --repo 0rl4nd0l/tenn --state all --search "<terms>"
rg -n "<issue|job_id|report|symptom|surface>" docs reports scripts tests backend frontend .github
```

Record `DATA_MISSING` instead of guessing when evidence, auth, reports, task cards, diffs, or validation output are unavailable.

## Context Hygiene

After each reviewed item, emit only the compact matrix row needed by the supervisor:

- Issue or artifact identifier.
- Decision.
- Branch, commit, and report.
- Validation result.
- Follow-up issue or parking link.
- Remaining `DATA_MISSING`.
- Next recommended issue when reviewing a batch.

Do not carry forward detailed logs, file excerpts, speculative hypotheses, issue-specific workaround assumptions, failed experiments, or unvalidated fix patterns.

## Review Passes

If Codex can safely use subagents, run these as independent named subagents with raw artifacts only. Do not pass the intended answer. Do not let subagents mutate GitHub or repo state. If subagents are unavailable, emulate the same passes in one response.

Run these passes:

- `Root Cause Reviewer`: decide whether the underlying defect was fixed or only the observed symptom.
- `Regression Reviewer`: check class-wide blast radius across tickers, source types, routes, docs, reports, jobs, workflows, and tests.
- `Security/Boundary Reviewer`: check task-card permissions, forbidden surfaces, secrets, auth, CI, repo-control, and runtime boundaries.
- `Financial Truth/Provenance Reviewer`: check canonical truth, source traceability, provenance labels, source pages, and no fabricated or relaxed labels.
- `User Value Reviewer`: check whether the issue's actual user/workflow value was restored and validated.
- `Branch Hygiene Reviewer`: when branch work is involved, check branch classification, merge readiness, validation, supersession, parking eligibility, and destructive-cleanup boundaries.
- `Skeptic/Opposition Reviewer`: argue the strongest reason this should remain open or be parked.
- `Final Arbiter`: reconcile the passes into a closeout verdict.

## Classification

Assign one or more solution classifications:

```text
ROOT_CAUSE_FIXED
NARROW_WORKAROUND
TEST_ONLY_COVERUP
PARTIAL_FIX
AUDIT_ONLY_NO_REMEDIATION
REGRESSION_RISK
NEEDS_FOLLOWUP
READY_TO_CLOSE
```

Use `ROOT_CAUSE_FIXED` only when the fix addresses the shared mechanism, includes focused validation, and does not depend on one ticker, one route, one source, one report, or one UI path unless the issue is truly isolated.

Use `TEST_ONLY_COVERUP` when tests, fixtures, labels, mocks, or assertions were changed to hide the failure without fixing the product or pipeline behavior.

Use `AUDIT_ONLY_NO_REMEDIATION` when the report is complete but no product/runtime/code/data remediation landed.

## Root-Cause Over Workaround Gate

If the classification is `NARROW_WORKAROUND`, `TEST_ONLY_COVERUP`, `PARTIAL_FIX`, `REGRESSION_RISK`, or `AUDIT_ONLY_NO_REMEDIATION`, the verdict cannot be `PASS_CLOSEOUT`.

Require a follow-up issue, parking link, `DATA_MISSING`, or a keep-open decision. Close only as audit complete when all remediation is tracked elsewhere.

## Blast Radius Gate

For bugs involving tickers, documents, news, retrieval, source labels, memory, extraction, or UI/backend contracts:

- Prove whether the issue is isolated or class-wide.
- Check other likely affected tickers, docs, routes, or classes where feasible.
- Require regression coverage or a follow-up issue if broader proof is missing.
- Reject one-off aliases, hidden fallbacks, label relaxation, and test-only coverups as final fixes.

## Maximum Value Fix Standard

Require the smallest safe system-level fix that addresses the class of problem. Reject both extremes:

- Too narrow: ticker-specific, route-specific, source-specific, or label-relaxing fixes that leave the same class broken elsewhere.
- Too broad: rewrites, architecture drift, hidden fallback behavior, uncontrolled runtime changes, or scope expansion beyond the task card.

The acceptable fix is evidence-backed, locally scoped, architecture-preserving, and validated against the real blast radius.

## Follow-Up Gate

Every unresolved `FOLLOWUP_REQUIRED` item must have one of:

- An existing open issue or PR that fully tracks it.
- An explicitly authorized new follow-up issue.
- A merge-parking entry for completed-but-unmerged work.
- `DATA_MISSING` with the exact missing evidence.

If any required follow-up is missing, the verdict cannot be `PASS_CLOSEOUT`.

## GitHub Backlog Integrity Gate

Review whether the proposed closeout preserves GitHub as Tenn's live actionable backlog. Reports, task cards, Project Memory, and merge parking can provide evidence, but unresolved actionable work must be visible through GitHub Issues, linked PRs, or explicit parking.

Check that each unresolved actionable finding is linked to an existing issue or PR, authorized for a new issue, parked for review, marked `NO_FOLLOWUP` with reason, or marked `DATA_MISSING` with exact evidence needed. If not, the verdict cannot be `PASS_CLOSEOUT`.

For any new or recommended follow-up issue, require:

- Recommended labels: `lane:*`, `mode:*`, `priority:*`, `risk:*`, `state:*`, and `type:*`.
- Recommended milestone: `M0 Control Plane Hardening`, `M1 Trust / Provenance Foundation`, `M2 Evaluation Spine`, `M3 Query + Memory Integrity`, `M4 Financial Truth Expansion`, `M5 Cockpit Analyst Workflow`, or `M6 Runtime / Local Automation`.
- Project field recommendations when Projects are available: Lane, Mode, Risk, Priority, Status, Task Card, Report Path, Blocked By, Root Cause Fixed, Follow-up Required, and Production Data Access.
- Task-card path, report path, allowed surfaces, forbidden surfaces, validation, hard stops, and definition of done.
- `## Summary` in plain language.

Check PR link language. `fixes #X` is valid only when product remediation landed and validation passed. Audit-only, report-only, exploratory, partial, or parked work must use `refs #X`, `audit for #X`, or normal references so GitHub does not auto-close unresolved remediation.

Before accepting a new follow-up, verify de-duplication against open issues, closed issues, open and closed PRs, recent reports, task cards, and merge parking entries. Similar symptoms are not enough; the existing tracker must cover the same root cause, lane, validation path, and hard stops.

Automated report findings should either create/draft issue-ready findings, update existing issue references when approved, or mark items `DEFER` / `NO_FOLLOWUP`. Disconnected local registries are not enough for `PASS_CLOSEOUT`.

## Review Matrix

Produce a matrix:

| Issue | Lane | Worker decision | Reviewer verdict | Closed? | Follow-up/Parking | DATA_MISSING | Next action |
| ----- | ---- | --------------- | ---------------- | ------- | ----------------- | ------------ | ----------- |

## Final Verdict

Return one final verdict:

```text
PASS_CLOSEOUT
PASS_WITH_FOLLOWUPS
KEEP_OPEN
PARK_FOR_REVIEW
BLOCKED_DATA_MISSING
FAIL_UNSAFE_OR_REGRESSIVE
```

Use `PASS_CLOSEOUT` only when `READY_TO_CLOSE` is justified, required follow-ups are linked, validation is fresh, and the close reason would not mislead a future agent.

Use `PASS_WITH_FOLLOWUPS` when the completed work is valid but bounded follow-ups remain and are already tracked.

Use `KEEP_OPEN` when the issue remains the best tracker, validation failed, remediation did not land, or follow-ups are not tracked.

Use `PARK_FOR_REVIEW` only for completed, validated, unmerged work with a visible parking or review path.

Use `BLOCKED_DATA_MISSING` when required evidence is unavailable.

Use `FAIL_UNSAFE_OR_REGRESSIVE` when the proposed closeout crosses boundaries, creates regression risk, hides failures, or misstates remediation.

## Output

Finish with:

```markdown
## Resolution review

## Summary
In plain language:
- What the issue was:
- How it was fixed, or why it was not fixed:
- What it impacted:
- How the result improves Tenn:
- Why this is a meaningful step forward or why it is not enough:

Reviewed:
- Issue/PR/report:
- Branch:
- HEAD:

Matrix:
| Issue | Lane | Worker decision | Reviewer verdict | Closed? | Follow-up/Parking | DATA_MISSING | Next action |
| ----- | ---- | --------------- | ---------------- | ------- | ----------------- | ------------ | ----------- |

Blast radius:
- Tickers:
- Sources/docs:
- Routes/workflows:
- Tests/validation:

Boundary compliance:
- Task-card permissions:
- Forbidden surfaces:
- Product remediation landed: YES / NO

GitHub backlog integrity:
- Labels recommended/applied:
- Milestone recommended/applied:
- Project fields recommended/applied:
- PR link mode: fixes / refs / audit for / none
- Required follow-ups tracked in GitHub/PR/parking: YES / NO

Branch hygiene:
- Branch classification:
- Merge readiness:
- Parking eligibility:
- Supersession:
- Destructive cleanup approved: NO

DATA_MISSING:
- ...

Verdict:
PASS_CLOSEOUT / PASS_WITH_FOLLOWUPS / KEEP_OPEN / PARK_FOR_REVIEW / BLOCKED_DATA_MISSING / FAIL_UNSAFE_OR_REGRESSIVE
```
