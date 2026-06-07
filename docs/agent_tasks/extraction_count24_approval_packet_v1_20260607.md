---
job_id: extraction_count24_approval_packet_v1_20260607
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Query Orchestration
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_count24_approval_packet_v1_20260607.md
  - reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/README.md
  - reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/approval_packet.json
  - reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/status.json
  - reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/validation.json
  - reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/raw_commands.log
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_count24_approval_packet_v1_20260607
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
allow_audit_code_changes: true
---

# Count-24 Approval Packet After PR #306

## Objective

Prepare the operator approval packet for a future bounded count-24 Tenn
extraction validation run from current canonical after PR #306.

## Scope

Mode: APPROVAL PACKET / REPORT ONLY.

Risk: MEDIUM/HIGH.

Canonical target:
`migration/clean-runtime-baseline-reconstruct-v1`.

Required canonical merge commit:
`b67736109db2c405171ff039c3b2f071238205db`.

Prior decision:
`READY_FOR_COUNT24_APPROVAL_PACKET`.

## Hard Stops

- Do not run count-24.
- Do not run count-32.
- Do not run broad extraction, broad backfill, full ticker-universe extraction,
  an extra count-16 sample, or any extraction sample.
- Do not mutate DB, Qdrant, news stores, memory, source PDFs, extraction code,
  prompts, gold labels, runtime config, schema, services, models, or GPU config.
- Do not perform source-PDF edits, unrelated cleanup, stash, reset, rebase,
  branch deletion, or canonical merge.
- Mark the future count-24 as `NOT_AUTHORIZED` unless the operator provides the
  exact approval phrase documented in the packet.

## Required Report Contents

- Exact operator approval language.
- Proposed seed and sample strategy.
- Candidate pool count/hash requirement.
- Selected-document manifest requirement.
- Runtime readiness gates.
- Queue, GPU, and process checks.
- Loaded commit proof handling.
- Accepted-output audit requirements.
- Side-effect audit requirements.
- Stop conditions.
- Containment plan if unsafe rows appear.
- Success/failure thresholds.
- Remaining risks and `DATA_MISSING`.
- Explicit confirmation that no count-24/count-32/extraction/backfill/full
  ticker run was executed while preparing this packet.

## Validation

- Validate this task card.
- JSON-validate report artifacts.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Verify no source PDFs are staged.
- Inspect registry active jobs through safe read-only evidence.
- Record final git status.
