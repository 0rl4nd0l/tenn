---
job_id: a2m_recall_chat_visible_evidence_gap_v1_20260526
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_recall_chat_visible_evidence_gap_v1_20260526.md
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/README.md
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/status.json
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/evidence_gap_analysis.json
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/runtime_probe.json
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/validation.json
  - reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/a2m_recall_chat_visible_evidence_gap_v1_20260526
mutation_mode: audit_only
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
production_data_access: false
github_mutation_allowed: branch_push_pr_and_issue_comment
related_issue: 87
---

# A2M Recall Chat Visible Evidence Gap

## Objective

Refresh #87 as a report-only audit: map the A2M recall answer's visible
evidence gaps to current code, adjacent trackers, and missing runtime evidence,
then decide whether implementation is safe.

## Scope

This task is audit-only. It may inspect the issue, adjacent issues/PRs,
evidence-guard code, tests, local service availability, and repo reports. It
must not run a chat prompt through live model/runtime services unless those
services are already available and a read-only smoke is safe.

## Contract Safety

- Target layer: Query Orchestration / Provenance audit only.
- Relevant contract: backend owns retrieval and authoritative data; Cockpit is
  a client/orchestration layer and must not invent or relabel evidence.
- Must not change: retrieval behavior, evidence labels, source assembly,
  evidence guard logic, DB, Qdrant, news stores, memory stores, canonical
  financial truth, parser routing, extraction prompts, gold labels,
  model/runtime/GPU/service config.
- GPU process check: not required; this audit does not spawn, restart, or
  depend on llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_recall_chat_visible_evidence_gap_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_recall_chat_visible_evidence_gap_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/a2m_recall_chat_visible_evidence_gap_v1_20260526.md --repo-root .`
- Adjacent issue/PR duplicate check.
- Read-only inspection of evidence-guard code and A2M news tests.
- Current localhost runtime availability probe.
- JSON validation.
- Path-redaction scan.
- `git diff --check`.
- task-card `check-diff`.
- registry release before final report.

## Hard Stops

- Exact prompt/session/source envelope remains missing.
- Current services are not already running for a safe read-only reproduction.
- Any fix would require source assembly or evidence-guard code without a proven
  root cause.
- Any fix would weaken `DATA_MISSING`, claim verification, or source-label
  semantics.
- Any proposed remediation is A2M-only rather than class-level.
