---
job_id: memory_fanout_suppression_quarantine_design_v1_20260524
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_fanout_suppression_quarantine_design_v1_20260524.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/README.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/status.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/fanout_suppression_design.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.csv
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/validation.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524
mutation_mode: audit_only
production_data_access: false
---

# Memory Fanout Suppression Quarantine Design

## Objective

Design the smallest safe way to prevent source-fanout suspicious company-memory rows from surfacing as trusted ticker/company context, without mutating live memory.

## Required Audit

- Read prior memory inventory/report artifacts if present.
- Identify the memory read/selection path that made suspicious entries selectable in dry-run scoring.
- Compare quarantine artifact, read-path filter, score penalty, migration cleanup proposal, evidence-role reclassification, alias/write-path prevention, and combinations.
- Evaluate blast radius, false-positive risk, deterministic detection limits, and user-review requirements.

## Allowed Work

- Report-local design and candidate quarantine artifacts derived from existing reports.
- Synthetic/read-path test plan or non-live scaffolding recommendation only if safe.

## Forbidden

- No live memory update, delete, rewrite, migration, alias canonicalisation, reindex/resync, or write-prone live chat smoke.
- No hiding memory context without visible `DATA_MISSING` or context labels unless explicitly tested and approved later.

## Validation

- Validate JSON/CSV report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
