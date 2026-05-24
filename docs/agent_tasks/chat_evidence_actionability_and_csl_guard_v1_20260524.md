---
job_id: chat_evidence_actionability_and_csl_guard_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md
  - reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/
  - reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/README.md
  - reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/diff-check.json
  - reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/status.json
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - cockpit-ui/lib/cockpit-chat-actionability.ts
  - cockpit-ui/lib/cockpit-chat-actionability.test.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Chat Evidence Actionability And CSL Guard

Audit-first safe-extension task to improve Cockpit chat evidence discipline and answer actionability, including a generic regression guard for CSL-style context-only filing evidence being treated as verified market or technical price-trend evidence.

The allowlist was narrowed after discovery to a frontend chat evidence-state helper, the existing terminal message shell, focused Vitest fixtures, the task card, and this job's report directory. Backend chat, retrieval, source ranking, financial truth, parser routing, data stores, runtime topology, and memory write paths are intentionally out of scope for this slice.
