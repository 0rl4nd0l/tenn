---
job_id: post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519
allowed_files:
  - docs/agent_tasks/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519.md
  - docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md
  - docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md
  - docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md
  - docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md
  - docs/agent_tasks/memory_contamination_live_inventory_readonly_v1_20260519.md
  - docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md
  - reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/
  - reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/README.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/a2m_trace_map.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/blast_radius_candidates.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/entity_linking_path.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/retrieval_path_trace.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/source_label_risk_matrix.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/status.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/validation_commands.json
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/README.md
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/diff-check.json
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/status.json
  - reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/README.md
  - reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/status.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/README.md
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/corpus_inventory.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json
  - reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/scorecard_proposal.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/README.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_contamination_summary.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_duplicate_clusters.csv
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/active_source_fanout_clusters.csv
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/candidate_entry_id_status_check.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/cleanup_readiness.md
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/db_path_resolution.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/diff-check.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/known_historical_source_checks.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/schema_inventory.json
  - reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/ticker_spot_checks.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/README.md
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/cleanup_plan_later.md
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/diff-check.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/memory_store_inventory.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/status.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/surfacing_risk_matrix.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/suspected_fanout_clusters.json
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/writer_path_trace.md
  - reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/README.md
  - reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/diff-check.json
  - reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/status.json
---

# Post-NVMe Memory/A2M Audit Artifact Checkpoint

Checkpoint recent audit and report artifacts after the memory contamination,
gold metric coverage, Cockpit chat orchestration, control-prompt guard, and A2M
news trace audits.

## Scope

- Preserve only the task cards and report artifacts listed in `allowed_files`.
- Do not modify source code, runtime config, scripts, data stores, DB files,
  Qdrant, model files, parser/extraction code, or Cockpit UI/source files.
- Copy artifacts from isolated worktrees only when they match the listed task
  cards and report directories.
- Stop if staging includes any file outside the listed task/report artifacts.

## Expected Output

- `reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/README.md`
- A commit containing only the allowed task cards and report artifacts.
