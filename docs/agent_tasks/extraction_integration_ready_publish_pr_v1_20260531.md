---
job_id: extraction_integration_ready_publish_pr_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_integration_ready_publish_pr_v1_20260531.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_integration_ready_publish_pr_v1_20260531/README.md
  - reports/agent_jobs/extraction_integration_ready_publish_pr_v1_20260531/status.json
  - reports/agent_jobs/extraction_integration_ready_publish_pr_v1_20260531/validation.json
  - reports/agent_jobs/extraction_integration_ready_publish_pr_v1_20260531/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_integration_ready_publish_pr_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: push_branch_and_open_draft_pr
related_issue: 97
---

# Extraction Integration Ready Publish PR

## Objective

Publish the clean integration branch
`integrate/extraction-metric-ontology-gate-v1-20260531` and open a draft PR
against `migration/clean-runtime-baseline-reconstruct-v1` so the metric
ontology gate, synced eval evidence, runtime approval preflight, and proof
matrix bundle can be reviewed without carrying the earlier WIP history.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-integration-ready-v1-20260531`.
- Branch: `integrate/extraction-metric-ontology-gate-v1-20260531`.
- Intended files: this task card, `docs/claude/STATE.md`, and this job report
  directory.
- External mutation: push current branch to `origin` and open one draft PR.
- Contested surfaces touched: none.
- Collision risk: LOW; branch is isolated and no existing PR for this head
  branch was found before the task card was written.
- Decision: proceed after task-card validation, registry overlap check, and
  claim.

## Contract Check

- Target system layer: Evaluation/reporting workflow only.
- Relevant contract rules: backend remains authoritative; extraction and metric
  truth are not changed by this publish action; scorecards remain evidence, not
  canonical write authorization.
- What must not change: runtime services, source PDFs, DB/Qdrant, parser
  routing, prompts, schemas, Cockpit UI, model/GPU config, and canary state.
- Why safe: the local integration commit is already validated and this task
  only makes it reviewable as a draft PR.
- GPU process check required: no. This task does not spawn, restart, or depend
  on llama-server.

## Validation

- Validate this task card.
- Check registry overlap and claim.
- Confirm branch is clean before publish.
- Confirm no existing PR for this head branch.
- Confirm `gh` is installed and authenticated.
- Push the branch to `origin`.
- Open a draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
- Capture PR URL/number and final branch state.
- Run task-card `check-diff`.
- Release registry claim.

## Forbidden

- Runtime startup/reload, canary execution, document submission, backfill.
- DB/Qdrant/source-PDF/canonical-truth mutation.
- Parser, prompt, schema, Cockpit UI, or model/GPU config mutation.
- Marking the full 10-item objective complete.
