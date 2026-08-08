---
job_id: cockpit_intel_pulse_signals_memory_capability_v1_20260531
lane: Reporting
supporting_lanes:
  - Memory
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_intel_pulse_signals_memory_capability_v1_20260531.md
  - reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531/README.md
  - reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531/status.json
  - reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531/validation.json
  - reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531/diff-check.json
  - reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531/capability_audit.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/cockpit_intel_pulse_signals_memory_capability_v1_20260531
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: pr_create
related_issue: 148
---

# Cockpit Intel Pulse Signals and Memory Capability Audit

## Objective

Decide, with current repo evidence, whether Intel Pulse Signals and Memory
stages should stay unavailable, be hidden behind an explicit capability state,
or be wired to backend-authoritative read contracts. This slice is report-only:
it must not implement the decision.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-reporting-intel-pulse-signals-memory-capability-v1-20260601`.
- Branch: `safe/reporting-intel-pulse-signals-memory-capability-v1-20260601`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Issue: #148.
- Primary lane: Reporting.
- Supporting lanes: Memory and Query Orchestration.
- Intended files: this task card and this job's report artifacts only.
- Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`
  inspected read-only for route-shape evidence, not edited.
- Collision risk: LOW because this is report-only and edits no product files.
- Decision: proceed as AUDIT MODE after validation, overlap check, and registry
  claim.

## Contract Check

- Target system layer: Reporting/client capability audit only.
- Relevant contract rules: backend remains the sole authority; Cockpit is a
  client/orchestration layer; Cockpit must not implement retrieval, storage, or
  alternate financial interpretations; memory and financial truth boundaries
  must stay provenance-bound.
- What must not change: backend route/service code, frontend product code,
  memory stores, retrieval, financial truth, source/evidence labels, Qdrant,
  Postgres, production data, runtime/model/GPU configuration, and service state.
- Why safe: this task records evidence and a recommended follow-up contract
  only. It does not wire data, hide UI, add endpoints, mutate memory, or run
  services.
- GPU process check required: no. This task does not spawn, restart, or depend
  on `llama-server`.

## Required Evidence

- Current `/intel-ops` page behavior for Signals and Memory stages.
- Current Intel Pulse client API calls and types.
- Current backend Intel Pulse response model and route family.
- Current backend service handling for `signal_count`, `memory_count`, Signals
  stage, and Memory stage.
- Prior frontend wiring audit evidence if present.
- Duplicate issue/PR and registry checks.

## Forbidden

- Editing product source files.
- Backend endpoint changes.
- Frontend behavior changes.
- Memory store writes or architecture changes.
- Synthetic Signals or Memory data presented as live/canonical.
- Production data access.
- Qdrant, Postgres, news, extraction, or financial truth mutation.
- Runtime/model/GPU/service config changes.
- Broad #53, #46, or unrelated frontend work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_intel_pulse_signals_memory_capability_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_intel_pulse_signals_memory_capability_v1_20260531.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_intel_pulse_signals_memory_capability_v1_20260531.md --repo-root .`
- Read-only evidence inspection using `sed`, `nl`, `rg`, and `gh issue view`.
- JSON validation for report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_intel_pulse_signals_memory_capability_v1_20260531.md --repo-root .`
- Registry release and final status check.

## Final Report Requirements

- Decision recommendation.
- Evidence table with file and line references.
- Explicit DATA_MISSING items.
- Follow-up implementation boundary.
- Exact validation commands and results.
- Explicit statement that no product, backend, memory, retrieval, financial
  truth, source-label, GPU, or runtime files were changed.
