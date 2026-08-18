---
job_id: github_outstanding_issue_creation_v1_20260526
lane: Evaluation
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/README.md
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/status.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/duplicate_search_matrix.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/created_issues.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/skipped_items.json
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md
  - reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/github_outstanding_issue_creation_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: github_issue_creation
allowed_github_mutation:
  - create missing GitHub issues only after duplicate search
  - apply existing labels/milestones only if available and unambiguous
  - optionally add a short comment to an existing issue only if needed to document why no duplicate was created
production_data_access: false
---

# GitHub Outstanding Issue Creation

Mode detail: issue management / audit first / GitHub mutation only if missing.

## Objective

Audit the current GitHub issue board for outstanding follow-ups from the recent
Cockpit ticker-news/source-grounding session. Create only missing GitHub issues
that are not already covered by existing open or closed issues or PRs.

## Lane

- Requested primary lane: Repo Hygiene.
- Validator lane: Evaluation, because the current task-card validator accepts
  only Financial Truth, Evaluation, Provenance, Query Orchestration, Memory, and
  Reporting.
- Supporting lanes: Reporting, Evaluation, Provenance, Query Orchestration.

## Allowed Scope

- Create this task card and the required report bundle.
- Inspect current repo state, task-card registry state, and GitHub issue/PR
  coverage.
- Search open and closed issues and PRs before creating anything.
- Create missing GitHub issues only when duplicate checks are clean.
- Apply existing labels and milestones only if available and unambiguous.
- Optionally add a short comment to an existing issue only if needed to
  document why a duplicate was not created.

## Candidate Issues

1. Repo Hygiene issue for the two persistent unrelated untracked task cards:
   - `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
   - `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
2. Optional Reporting/Provenance issue for Cockpit UI/source-drawer semantics
   if no existing tracker covers whether `context_only`, no-hit, degraded,
   `DATA_MISSING`, unknown, or unverified sources can be overstated as
   source-backed or claim-verified.

## Known Covered Items

Do not create duplicate issues for:

- `#83` news projection/materialization/parity repair planning.
- `#84` `cockpit_announcement_context` runtime schema audit.
- `#87` A2M recall chat answer visible evidence / `DATA_MISSING`
  evidence-envelope gap.
- `#88` memory system fitness audit.

Do not create retroactive open issues for already landed and validated work:

- status/news-health route contract.
- ticker-universe local-news/source-grounding honesty guard.
- ticker-news retrieval/ranking/source-pack handoff.
- strict literal `local_news_context` route.
- natural-language local-news intent route at canonical HEAD
  `61723bdca4ea30ce404d606cec63e47b9cb739b3`.

Do not create a GitHub issue for Project Memory `/save`.

## Forbidden

- Product/backend/frontend/runtime code changes.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime, model, GPU, or service config edits.
- Closing GitHub issues without validation evidence.
- Creating duplicate issues.
- Editing existing issue bodies unless explicitly needed and reported.
- Pull request creation.
- Branch delete, prune, reset, stash, rebase, or merge.
- Cleaning, stashing, resetting, deleting, or otherwise mutating unrelated
  files.
- Committing the two unrelated task cards unless separately authorized.

## Required Preflight

- Record `pwd`, branch, HEAD, `git status --short --untracked-files=all`,
  `git worktree list`, and recent commits.
- Run registry `list-active`, `check-overlap`, and claim only if supported and
  safe.
- Validate this task card.
- Confirm GitHub owner/repo, auth status, and issue creation permission.
- Search open and closed issues plus PRs before creating anything.

## Required Duplicate Searches

For untracked task-card hygiene:

- `untracked task cards`
- `a2m_backend_reload_news_status_activation_smoke`
- `automation_audit_issue_preservation`
- `MILESTONE NOT COMMITTED task cards`
- `check-diff untracked task cards`
- `worktree task-card hygiene`

For UI/source drawer semantics:

- `source drawer semantics`
- `source-backed UI source drawer`
- `context_only source-backed`
- `no-hit degraded source drawer`
- `source label UI context_only`
- `claim_verified source drawer`
- `source label fixture matrix`

For already-covered items:

- `cockpit_announcement_context`
- `news projection materialization parity`
- `A2M recall visible evidence`
- `natural language local news intent`
- `latest local news BHP`

## Required Outputs

- `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/README.md`
- `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/status.json`
- `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/duplicate_search_matrix.json`
- `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/created_issues.json`
- `reports/agent_jobs/github_outstanding_issue_creation_v1_20260526/skipped_items.json`

## Acceptance Criteria

- Missing GitHub issues are created only where duplicate checks are clean.
- Already-covered issues are not duplicated.
- Already-landed work does not get new open issues.
- The report bundle records exactly what was created and why.
- No product, runtime, or data surfaces are changed.

## Validation

- Task-card validate/check-diff.
- Registry list/check-overlap/claim/release if available and safe.
- GitHub issue/PR duplicate search.
- JSON validation for report artifacts.
- `git diff --check`.
- Final git status.

## Hard Stops

- Duplicate tracker found.
- Active registry conflict that creates unresolved HIGH collision risk.
- Missing GitHub auth or issue creation permission.
- Forbidden repo, product, runtime, data, or GitHub mutation requirement.
- Need to delete, stash, reset, clean, merge, rebase, prune, or create a PR.
