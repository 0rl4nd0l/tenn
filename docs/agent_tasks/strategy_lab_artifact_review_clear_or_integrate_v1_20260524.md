---
job_id: strategy_lab_artifact_review_clear_or_integrate_v1_20260524
lane: Reporting
owner: Codex
supporting_lanes:
  - Repo Hygiene
  - Evaluation
mutation_mode: audit_only
allow_audit_code_changes: true
approval_required: false
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_artifact_review_clear_or_integrate_v1_20260524.md
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/diff-check.json
---

# Strategy Lab Artifact Review Clear Or Integrate v1

## Objective

Determine whether the canonical Tenn checkout is clear enough to integrate the
already validated read-only Strategy Lab artifact review value layer. If the
canonical gates are not clear, continue by report-only audit or by validating
the isolated patch in a clean temporary worktree without touching unrelated
task-card dirt.

## Scope

This task starts as audit-only. Do not stage, cherry-pick, copy isolated patch
files, commit, or otherwise mutate integration files until all canonical gates
are clean and a separate exact-allowlist safe-extension integration task card
exists.

The value layer remains Cockpit read-only reporting: no real QuantDinger
transport, no trading, no canonical financial truth, no store writes, and no
runtime/store integration.

## Allowed Files During Audit

Only this task card and this task report bundle may be written by this audit.

## Required Checks

- Canonical preflight: realpath, branch, HEAD, status, and worktree list.
- Validate this task card.
- Registry `list-active` and `check-overlap`.
- Check whether the known unrelated task-card blockers are still present.
- Confirm the isolated value-layer worktree exists and record branch/HEAD/status.
- If canonical gates are still blocked, do not touch unrelated task cards.
- If useful, validate the isolated patch in a clean temporary worktree from
  canonical HEAD and report the result without merging back.

## Forbidden

- Do not touch unrelated task-card blockers except to inspect and report
  presence.
- No real QuantDinger transport/client/MCP/API implementation.
- No trading, broker, paper/live execution, tokens, market orders, or portfolio
  mutation.
- No DB, Qdrant, news, memory, canonical financial truth, artifact store, or
  promotion workflow writes.
- No parser, extraction, gold-label, runtime, model, GPU, dependency, or
  service changes.
- No dependency installation.
- No unrelated repo-hygiene cleanup.

## Deliverables

- `reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_artifact_review_clear_or_integrate_v1_20260524/status.json`
