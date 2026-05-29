---
job_id: extraction_real_gold_source_path_resolver_draft_pr_v1_20260529
lane: Evaluation
supporting_lanes:
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529.md
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529/README.md
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529/status.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: draft_pr_create_only
related_issue: 96
---

# Extraction Real-Gold Source Path Resolver Draft PR V1

## Objective

Create a draft PR for the already-pushed branch
`safe/extraction-real-gold-source-path-resolver-v1-20260529`, targeting
`migration/clean-runtime-baseline-reconstruct-v1`, so the real-gold source path
resolver fix has a review surface before integration.

## Scope

- Primary lane: Evaluation.
- Supporting lane: Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-real-gold-source-path-resolver-v1-20260529`.
- Base branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- GitHub mutation allowed: draft PR creation only.

## Contract Check

Target system layer: Evaluation/Provenance review visibility for an
already-validated test/report branch. This task does not invoke ingestion,
extraction, storage, retrieval, analysis, or client runtime code.

Relevant contract rules: backend financial truth remains source-bound; opening a
draft PR cannot promote canonical truth, mutate source assets, or authorize
runtime extraction.

What must not change: production extraction/backfill behavior, canonical
financial truth persistence, DB/Qdrant/news/memory stores, source PDFs, parser
routing, extraction prompts, metric ontology, scale/period semantics,
runtime/model/GPU/service config, schemas, Cockpit UI, issue state, issue
comments, labels, milestones, and non-draft PR state.

Why safe: this task only creates one draft PR from an already-pushed branch
after verifying no existing PR for the branch. It does not merge the branch,
mutate issue #96, or claim graduation.

GPU process check required: no. This task must not start, restart, stop, or
depend on `llama-server` and must not run live extraction jobs.

## Hard Stops

- Do not create a ready-for-review PR.
- Do not comment on, close, label, milestone, or edit GitHub issues.
- Do not merge the PR.
- Do not push, reset, or force-push the live baseline branch.
- Do not run canary, extraction, backfill, or runtime reload.
- Do not mutate production DB, Qdrant, news, memory, source PDFs, or canonical
  financial truth.

## Required Behavior

- Validate and claim this task card.
- Confirm no existing PR exists for this head branch.
- Create one draft PR targeting `migration/clean-runtime-baseline-reconstruct-v1`.
- Record PR URL/number and final local/remote branch heads in the report.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529.md --repo-root .`
- `gh pr list --state all --head safe/extraction-real-gold-source-path-resolver-v1-20260529`
- `gh pr create --draft --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/extraction-real-gold-source-path-resolver-v1-20260529`
- `gh pr view <number> --json number,title,state,isDraft,headRefName,baseRefName,url`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_source_path_resolver_draft_pr_v1_20260529.md --repo-root .`
- Registry release and final active-job read-only check.

## Final Report Requirements

Report branch, local head, remote head, PR URL/number, worktree, task card,
validation commands and results, confirmation that no issue/runtime/datastore
mutation occurred, and remaining #96 blocker.
