# GitHub Outstanding Issue Creation v1

## Preflight

- Agent: Codex
- Requested lane: Repo Hygiene
- Validator lane: Evaluation
- Execution mode: ISSUE MANAGEMENT / AUDIT FIRST / GITHUB MUTATION ONLY IF MISSING
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Start HEAD: `61723bdca4ea30ce404d606cec63e47b9cb739b3`
- Task card: `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`
- Contested product surfaces touched: none

The task-card validator does not accept `Repo Hygiene` as a frontmatter lane or
`github_issue_creation` as a frontmatter `mutation_mode`, so the card records
those requested values as `requested_primary_lane` and
`requested_mutation_mode` while using validator-compatible frontmatter.

## Registry Status

- `python3 scripts/agent_job_registry.py list-active`: one active job,
  `cockpit_watchlist_empty_state_actionability_v1_20260526`, on a separate
  worktree and file set.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`:
  failed because the two pre-existing untracked task cards are dirty outside
  this task card's allowed files.
- Registry claim: skipped because `check-overlap` was not claim-safe.
- Release: not applicable because no claim was created.

## GitHub Repo

- Repository inspected: `0rl4nd0l/tenn`
- URL: `https://github.com/0rl4nd0l/tenn`
- Viewer permission: `ADMIN`
- Issues enabled: true
- Issue creation permission: confirmed by successful issue creation
- Existing labels/milestones used only when present and unambiguous.

## Duplicate Searches Performed

Required search groups were run against open and closed issues plus PRs:

- Untracked task-card hygiene: `untracked task cards`,
  `a2m_backend_reload_news_status_activation_smoke`,
  `automation_audit_issue_preservation`,
  `MILESTONE NOT COMMITTED task cards`,
  `check-diff untracked task cards`, `worktree task-card hygiene`.
- UI/source drawer semantics: `source drawer semantics`,
  `source-backed UI source drawer`, `context_only source-backed`,
  `no-hit degraded source drawer`, `source label UI context_only`,
  `claim_verified source drawer`, `source label fixture matrix`.
- Already-covered items: `cockpit_announcement_context`,
  `news projection materialization parity`, `A2M recall visible evidence`,
  `natural language local news intent`, `latest local news BHP`.

Immediate pre-create duplicate checks were also run for the two final issue
titles/task IDs.

## Issues Created

- #94: `[Repo Hygiene] Classify and preserve two unrelated untracked task cards`
  - URL: `https://github.com/0rl4nd0l/tenn/issues/94`
  - Labels: `lane:repo-hygiene`, `lane:reporting`, `mode:audit`,
    `priority:p1`, `risk:medium`, `state:ready`, `type:control-plane`
  - Milestone: `M0 - Control Plane Hardening`
- #95: `[Reporting] Audit Cockpit source drawer semantics for context-only and degraded evidence`
  - URL: `https://github.com/0rl4nd0l/tenn/issues/95`
  - Labels: `lane:reporting`, `lane:provenance`,
    `lane:query-orchestration`, `mode:audit`, `priority:p1`, `risk:medium`,
    `state:ready`, `type:validation-gap`
  - Milestone: `M1 - Trust / Provenance Foundation`

## Skipped Items

- #83 already covers news projection/materialization/parity repair planning.
- #84 already covers `cockpit_announcement_context` runtime schema audit.
- #87 already covers the A2M recall visible evidence / `DATA_MISSING`
  evidence-envelope gap.
- #88 already covers memory system fitness audit.
- #71 is adjacent for source-label fixture coverage but does not directly
  cover UI/source-drawer rendering semantics, so it was not treated as a
  duplicate of #95.
- Landed and validated route/source-pack milestones were not turned into new
  retroactive open issues.
- Project Memory `/save` was not turned into a GitHub issue.

## DATA_MISSING

- Project board fields were not inspected or mutated.
- Registry claim could not be created because the two pre-existing untracked
  task cards remain outside this task card's allowed files.
- The UI/source drawer concern is a validation gap, not a confirmed UI bug from
  this run. Static inspection found existing chat/Home tests for several
  source-state distinctions, but no dedicated source-drawer audit tracker.

## Final Git Status

`git status --short --untracked-files=all` after report generation and
validation:

```text
?? docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md
?? docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md
?? docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
```

The report bundle is under an ignored `reports/` path and is visible with
`git status --short --ignored=matching --untracked-files=all
reports/agent_jobs/github_outstanding_issue_creation_v1_20260526` as:

```text
!! reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/
```

This task intentionally did not clean, delete, stash, reset, move, or commit the
two unrelated task cards.

## Validation

- Task-card validate: PASS.
- GitHub auth/repo/permission check: PASS.
- Duplicate search across open/closed issues and PRs: PASS.
- Created issue verification via `gh issue view`: PASS for #94 and #95.
- JSON validation for report artifacts: PASS.
- `git diff --check`: PASS.
- Task-card `check-diff`: BLOCKED by the two pre-existing unrelated untracked
  task cards, matching the repo-hygiene issue created as #94. No product,
  runtime, data, or unrelated tracked file was changed.

## Save Recommendation

Do not create a GitHub issue for Project Memory `/save`. Treat it as a Project
Memory consolidation item if the user asks to preserve the session summary.
