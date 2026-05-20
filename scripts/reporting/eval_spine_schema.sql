-- Offline Evaluation Spine DuckDB schema.
-- This schema is for report-local analysis only. It is not a backend migration.

CREATE TABLE IF NOT EXISTS artifact_runs (
  run_id VARCHAR PRIMARY KEY,
  job_id VARCHAR,
  lane VARCHAR,
  mode VARCHAR,
  status VARCHAR,
  branch VARCHAR,
  head VARCHAR,
  base_head VARCHAR,
  worktree VARCHAR,
  task_card_path VARCHAR,
  output_dir VARCHAR,
  production_data_access BOOLEAN,
  started_at VARCHAR,
  completed_at VARCHAR,
  save_recommendation VARCHAR,
  source_artifact_path VARCHAR,
  payload_json VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_cards (
  task_card_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  job_id VARCHAR,
  path VARCHAR,
  sha256 VARCHAR,
  validation_ok BOOLEAN,
  validation_issues_json VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS validation_commands (
  validation_command_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  command VARCHAR,
  cwd VARCHAR,
  result VARCHAR,
  exit_code INTEGER,
  notes VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS artifact_files (
  artifact_file_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  path VARCHAR,
  artifact_type VARCHAR,
  sha256 VARCHAR,
  schema_name VARCHAR,
  notes VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scorecard_results (
  scorecard_result_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  scorecard_profile VARCHAR,
  status VARCHAR,
  document_count INTEGER,
  metric_check_count INTEGER,
  eligible_metric_count INTEGER,
  candidate_count INTEGER,
  ambiguous_count INTEGER,
  unsupported_count INTEGER,
  data_missing_count INTEGER,
  overclaim_guard VARCHAR,
  payload_json VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metric_expectations (
  metric_expectation_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  scorecard_profile VARCHAR,
  company VARCHAR,
  ticker VARCHAR,
  document_id VARCHAR,
  metric_name VARCHAR,
  expected_value DOUBLE,
  expected_unit VARCHAR,
  expected_period VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metric_results (
  metric_result_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  scorecard_profile VARCHAR,
  company VARCHAR,
  ticker VARCHAR,
  document_id VARCHAR,
  metric_name VARCHAR,
  actual_value DOUBLE,
  expected_value DOUBLE,
  status VARCHAR,
  data_missing BOOLEAN,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runtime_smokes (
  runtime_smoke_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  runtime_surface VARCHAR,
  runtime_target VARCHAR,
  endpoint_url VARCHAR,
  model_label VARCHAR,
  gpu_name VARCHAR,
  request_count INTEGER,
  pass_count INTEGER,
  degraded BOOLEAN,
  verdict VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS route_smokes (
  route_smoke_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  route_path VARCHAR,
  route_owner VARCHAR,
  expected_status_code INTEGER,
  actual_status_code INTEGER,
  classification VARCHAR,
  expected_presence BOOLEAN,
  observed_presence BOOLEAN,
  is_failure BOOLEAN,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_label_checks (
  source_label_check_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  surface VARCHAR,
  source_coverage_status VARCHAR,
  missing_required_evidence BOOLEAN,
  no_hit BOOLEAN,
  context_only BOOLEAN,
  claim_verified BOOLEAN,
  guard_action VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memory_audit_results (
  memory_audit_result_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  row_total INTEGER,
  active_row_count INTEGER,
  duplicate_cluster_count INTEGER,
  source_fanout_cluster_count INTEGER,
  manual_review_active_count INTEGER,
  untrusted_memory BOOLEAN,
  cleanup_readiness VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_trace_results (
  news_trace_result_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  ticker VARCHAR,
  trace_scope VARCHAR,
  ingestion_status VARCHAR,
  entity_link_status VARCHAR,
  sqlite_status VARCHAR,
  qdrant_status VARCHAR,
  rag_query_status VARCHAR,
  backend_chat_status VARCHAR,
  no_hit BOOLEAN,
  missing_required_evidence BOOLEAN,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dirty_worktree_events (
  dirty_worktree_event_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  path VARCHAR,
  status VARCHAR,
  allowed_by_task_card BOOLEAN,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_events (
  registry_event_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  job_id VARCHAR,
  lane VARCHAR,
  status VARCHAR,
  branch VARCHAR,
  worktree VARCHAR,
  claimed_at VARCHAR,
  released_at VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_missing_items (
  data_missing_item_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  field VARCHAR,
  code VARCHAR,
  class VARCHAR,
  description VARCHAR,
  blocked_by_policy BOOLEAN,
  blocked_by_environment BOOLEAN,
  expected_empty_state BOOLEAN,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS decisions_and_verdicts (
  decision_verdict_id VARCHAR PRIMARY KEY,
  run_id VARCHAR,
  verdict VARCHAR,
  truth_status VARCHAR,
  confidence VARCHAR,
  notes VARCHAR,
  source_artifact_path VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
