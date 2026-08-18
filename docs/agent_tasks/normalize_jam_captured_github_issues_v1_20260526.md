---
job_id: normalize_jam_captured_github_issues_v1_20260526
lane: Reporting
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/normalize_jam_captured_github_issues_v1_20260526.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/README.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/status.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/before_after_matrix.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/before_after_matrix.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/duplicate_search_matrix.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_decisions.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/github_readback.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/validation.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/diff-check.json
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_40.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_41.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_53.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_55.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_61.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_body_updates/issue_106_closeout_comment.md
allowed_repo_files:
  - docs/agent_tasks/normalize_jam_captured_github_issues_v1_20260526.md
  - reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: github_issue_normalization
allowed_github_mutation:
  - "edit issue bodies for #40, #41, #53, #55, and #61 only"
  - "apply existing labels to #40, #41, #53, #55, and #61 only"
  - "remove obsolete generic bug label from #41 only after replacing with contract labels"
  - "apply existing milestones to #40, #41, #53, #55, and #61 only"
  - "add a closeout comment to #106 only if every target issue is classified"
  - "close #106 only if every target issue is normalized, linked, superseded, or explicitly DATA_MISSING"
  - "update #106 labels only for closeout state if it closes"
production_data_access: false
---

# Normalize Jam-Captured GitHub Issues

Mode detail: audit-first / safe-extension GitHub issue normalization.

## Objective

Normalize raw or under-specified GitHub issues identified by #106 into the
current Tenn issue contract, without product/runtime/data changes and without
bypassing the GitHub Issue System Protocol.

## Target Issues

- #40 `failure to request a search`
- #41 `missing data`
- #53 `Production Cockpit forms rely on placeholders and unlabeled icon controls`
- #55 `Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound`
- #61 `Cockpit should default visible GPU to the llama-server GPU`

## Required Decisions

Each target issue must be classified as one of:

- normalized in place;
- linked to an existing issue;
- converted to a follow-up issue;
- marked duplicate or superseded;
- left `DATA_MISSING` with exact missing evidence.

## Required Contract Fields

Each normalized or classified issue must include:

- lane;
- mode;
- priority;
- risk;
- type;
- state;
- milestone;
- source evidence;
- why it matters;
- required task card path;
- required report path;
- allowed files/surfaces;
- forbidden files/surfaces;
- validation;
- hard stops;
- definition of done;
- `DATA_MISSING`;
- follow-up, parking, or dependency links.

## Allowed Scope

- Read-only repo, task-card, report, Jam, GitHub issue, GitHub PR, label, and
  milestone inspection.
- Write this task card and the declared report bundle.
- Edit only target issue bodies, labels, and milestones as listed in
  `allowed_github_mutation`.
- Close #106 only if the closeout gate is satisfied.

## Forbidden

- Product/backend/frontend/runtime code changes.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Model/runtime/GPU/service config changes.
- Branch cleanup, merge, rebase, reset, stash, prune, or delete.
- Broad issue closeout.
- Unrelated issue edits.
- Pull request mutation.
- Editing issue bodies in a way that loses original Jam evidence.

## Required Outputs

- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/README.md`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/status.json`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/before_after_matrix.md`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/before_after_matrix.json`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/duplicate_search_matrix.json`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/issue_decisions.json`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/github_readback.json`
- `reports/agent_jobs/normalize_jam_captured_github_issues_v1_20260526/validation.json`

## Validation

- Print branch, HEAD, status, remote, and worktree.
- Registry `list-active --read-only`.
- Read #106 and all target issues.
- Duplicate/supersession searches for each target.
- Jam evidence check for Jam-captured #40 and #41.
- Task-card validate/check-diff.
- Read back every edited or linked issue.
- Confirm labels and milestones.
- JSON validation for report artifacts.
- `git diff --check`.
- Final registry `list-active --read-only`.
- Final git status.

## Hard Stops

- Target issue identity cannot be established.
- Duplicate/supersession cannot be decided or represented as `DATA_MISSING`.
- Required GitHub mutation would touch unrelated issues.
- GitHub or Jam access is unavailable and cannot be represented as
  `DATA_MISSING`.
- Active registry overlap creates unresolved HIGH collision risk.
- Any forbidden product, runtime, data, memory, branch, PR, or service mutation
  would be required.
