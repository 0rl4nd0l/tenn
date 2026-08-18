---
job_id: cockpit_recent_sources_source_kind_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/api/commentary.py
  - financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py
  - cockpit-ui/components/cockpit/chat/sources-drawer.tsx
  - cockpit-ui/components/cockpit/chat/sources-drawer.test.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/README.md
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/status.json
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/validation.json
  - reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_recent_sources_source_kind_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - issue #213
docs_changed: []
docs_followup: NONE
reason: "Issue #213 asks for a focused UI/API attachment metadata contract fix; no durable docs routing or runtime operation changes."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend response-contract and Cockpit UI callback change with tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; scope is narrow and same-surface coordination is simpler in one worktree."
escalation_needed: false
related_issue: 213
---

# Cockpit Recent Sources Source Kind Contract

## Objective

Close issue #213 by preserving the attached-source `source_kind` contract when a
source is reattached from the Cockpit Recent sources drawer.

## Scope

- Extend `/api/cockpit/commentary/recent` data with a deterministic
  `source_kind` for supported recent commentary source types.
- Preserve that kind through `SourcesDrawer` item typing and `onReattach`.
- Reattach Recent sources in `chat-screen.tsx` using the drawer-provided kind
  instead of hardcoding every recent source as `ephemeral`.
- Add focused backend and UI tests for non-ephemeral recent sources.

## Hard Stops

- Do not mutate DB, Qdrant, news stores, memory stores, source PDFs,
  extraction outputs, gold labels, runtime/model/GPU/service config, or
  production data.
- Do not weaken evidence/source labels or mark context-only evidence as
  verified.
- Do not redesign chat retrieval, source drawer visuals, or upload auth flows.
- Stop if same-file owner overlap appears.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Focused backend recent endpoint tests.
- Focused SourcesDrawer UI tests.
- Type/lint check for touched UI files where available.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff` and `check-report-artifacts`.
