---
job_id: memory_contamination_root_cause_v1
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_contamination_root_cause_v1.md
  - reports/agent_jobs/memory_contamination_root_cause_v1/README.md
  - reports/agent_jobs/memory_contamination_root_cause_v1/status.json
  - reports/agent_jobs/memory_contamination_root_cause_v1/validation.json
  - reports/agent_jobs/memory_contamination_root_cause_v1/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/memory_contamination_root_cause_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #36 by validating the existing memory contamination root-cause
audit family into the issue-exact report path.

# Scope

Use current repo evidence and existing report artifacts to classify #36 as an
audit acceptance closeout only. Preserve all cleanup, quarantine, and live-row
handling as explicit follow-up work.

# Hard Boundaries

- Do not open or mutate live production memory stores for this closeout.
- Do not delete, expire, rewrite, quarantine, migrate, canonicalize, reindex,
  backfill, or resync memory/news/Qdrant/data stores.
- Do not edit memory writer paths, reader paths, Query Orchestrator, source
  registry, DB, Qdrant, news, canonical financial truth, parser/extraction,
  runtime, model, or service configuration.
- Mutate only this task card and listed issue-exact report artifacts.

# Required Outputs

- `reports/agent_jobs/memory_contamination_root_cause_v1/README.md`
- Current validation status.
- References to the existing root-cause audit, live read-only inventory, and
  quarantine-design evidence.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
current branch/HEAD/status/worktree-list evidence, existing artifact JSON
checks, `git diff --check`, and task-card check-diff.
