---
job_id: extraction_ctn_quarterly_source_type_pr_prep_v1_20260608
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_ctn_quarterly_source_type_pr_prep_v1_20260608.md
  - docs/agent_tasks/extraction_ctn_quarterly_source_type_precedence_v1_20260608.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/README.md
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_precedence_v1_20260608/validation.json
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_pr_prep_v1_20260608/README.md
  - reports/agent_jobs/extraction_ctn_quarterly_source_type_pr_prep_v1_20260608/validation.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_ctn_quarterly_source_type_pr_prep_v1_20260608
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: draft_pr_only
---

# CTN Quarterly Source-Type PR Prep

## Objective

Publish the CTN-only quarterly source-type precedence safe extension as a draft
PR from a clean current-origin branch.

## Branch

- Source worktree:
  `/home/l4nd0/tenn-ctn-quarterly-source-type-pr-v1-20260608`
- Source branch:
  `safe/extraction-ctn-quarterly-source-type-precedence-pr-v1-20260608`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`

## Allowed GitHub Mutation

GitHub mutation is limited to:

- pushing
  `safe/extraction-ctn-quarterly-source-type-precedence-pr-v1-20260608`;
- opening one draft PR against
  `migration/clean-runtime-baseline-reconstruct-v1`; and
- reporting the PR URL in this task's report.

Do not merge, mark ready for review, close/reopen/edit unrelated PRs, create or
edit issues, label, milestone, assign, or comment on GitHub.

## Required Local Validation

- Validate this task card.
- Run registry `list-active --read-only`.
- Recheck no duplicate PR exists for this branch or CTN commit.
- Run focused pytest for
  `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`.
- Run CTN-only saved-artifact scorecard replay, no extraction.
- JSON-validate report artifacts.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Verify only allowed files are changed/staged.

## Hard Stops

- Do not include HUB or LBL in this PR.
- Do not run count-24, count-32, random samples, broad extraction, backfill,
  full ticker extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, runtime/service/model/GPU config, schema, or production data.
- Do not touch PR #326/news files.
- Do not use PR #318 as a patch source.
- Stop if an existing PR already covers this branch or commit.
