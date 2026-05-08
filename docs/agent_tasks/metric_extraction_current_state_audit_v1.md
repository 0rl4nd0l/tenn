---
job_id: metric_extraction_current_state_audit_v1
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/metric_extraction_current_state_audit_v1.md
  - reports/agent_jobs/metric_extraction_current_state_audit_v1/
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/metric_extraction_current_state_audit_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit Tenn's current metric extraction system, runtime, accuracy, speed, evidence binding, and recent changes. Produce a full report only. Do not implement fixes.

# Hard boundaries

Do not edit:
- extraction logic
- extraction prompts
- parser routing
- gold labels
- evaluator scoring rules
- trust semantics
- canonical financial-truth writes
- production DBs
- Qdrant
- source PDFs
- runtime config
- Cockpit UI code, unless only inspected and reported

# Validation

Run only read-only checks, existing tests, existing eval harnesses, and runtime probes. Any generated eval outputs must stay under reports/agent_jobs/metric_extraction_current_state_audit_v1/.

# Final report

Required files:
- reports/agent_jobs/metric_extraction_current_state_audit_v1/README.md
- reports/agent_jobs/metric_extraction_current_state_audit_v1/runtime_inventory.json
- reports/agent_jobs/metric_extraction_current_state_audit_v1/recent_changes.md
- reports/agent_jobs/metric_extraction_current_state_audit_v1/accuracy_scorecard.md
- reports/agent_jobs/metric_extraction_current_state_audit_v1/performance_scorecard.md
- reports/agent_jobs/metric_extraction_current_state_audit_v1/failure_modes.md
- reports/agent_jobs/metric_extraction_current_state_audit_v1/next_fix_plan.md
- include raw command output snippets or logs where useful
