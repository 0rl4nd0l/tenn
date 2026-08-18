---
job_id: cockpit_news_context_date_filter_publish_v1_20260609
lane: Reporting
supporting_lanes:
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_news_context_date_filter_publish_v1_20260609.md
  - reports/agent_jobs/cockpit_news_context_date_filter_publish_v1_20260609/README.md
  - reports/agent_jobs/cockpit_news_context_date_filter_publish_v1_20260609/status.json
  - reports/agent_jobs/cockpit_news_context_date_filter_publish_v1_20260609/validation.json
  - reports/agent_jobs/cockpit_news_context_date_filter_publish_v1_20260609/diff-check.json
approval_required: true
approval_reference: "User said proceed after commit a91d09ca and next safe step was push/open a small PR."
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_news_context_date_filter_publish_v1_20260609
mutation_mode: safe_extension
requested_mutation_mode: publish_pr_only
production_data_access: false
github_mutation_allowed: push_branch_and_open_draft_pr_only
---

# Cockpit News Context Date Filter Publish

## Objective

Publish the already-committed Cockpit news-context date-filter follow-up branch
and open one draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.

## Scope

Mode: SAFE_EXTENSION.

Allowed GitHub mutations are limited to:

- Push branch `safe/cockpit-news-context-date-filter-v1-20260609`.
- Open one draft PR from that branch to
  `migration/clean-runtime-baseline-reconstruct-v1`.

## Hard Stops

- Do not merge the PR.
- Do not mark the PR ready for review.
- Do not create, edit, label, comment on, close, or reopen issues.
- Do not delete branches, refs, worktrees, or stashes.
- Do not mutate DB, Qdrant, Redis, news stores, source PDFs, prompts, gold
  labels, model/GPU config, or production data.
- Do not modify runtime code under this publish card.
- Stop if a PR already exists for the branch.

## Required Output

- Pushed branch readback.
- Draft PR URL and readback.
- Report artifacts with validation and mutation summary.
