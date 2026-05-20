-- Tenn Evaluation Spine v1 - proposed offline DuckDB schema.
-- Scope: report/eval artifacts only. Do not load production DBs, Qdrant,
-- memory stores, news stores, or backend request paths into this schema.

create table if not exists artifact_runs (
    run_id text primary key,
    job_id text,
    artifact_family text not null,
    lane text,
    mode text,
    branch text,
    head text,
    worktree text,
    output_dir text,
    task_card_path text,
    started_at timestamptz,
    completed_at timestamptz,
    collected_at timestamptz default now(),
    source_manifest_path text,
    source_manifest_sha256 text,
    production_data_access boolean default false,
    verdict text,
    truth_status text,
    save_recommendation text,
    overclaim_guard text,
    notes text
);

create table if not exists task_cards (
    task_card_id text primary key,
    run_id text references artifact_runs(run_id),
    job_id text,
    task_card_path text not null,
    task_card_sha256 text,
    lane text,
    owner text,
    mutation_mode text,
    production_data_access boolean,
    approval_required boolean,
    timeout_seconds bigint,
    output_dir text,
    allowed_files_json json,
    validation_ok boolean,
    validation_issues_json json,
    allow_audit_code_changes boolean,
    allow_unapproved_safe_extension boolean
);

create table if not exists validation_commands (
    validation_command_id text primary key,
    run_id text references artifact_runs(run_id),
    command_text text not null,
    cwd text,
    command_class text,
    result_status text,
    exit_code integer,
    elapsed_seconds double,
    output_artifact_path text,
    blocking_reason text,
    notes text
);

create table if not exists artifact_files (
    artifact_file_id text primary key,
    run_id text references artifact_runs(run_id),
    path text not null,
    artifact_type text,
    file_type text,
    sha256 text,
    byte_size bigint,
    machine_readable boolean,
    schema_name text,
    parse_status text,
    referenced_by_manifest boolean default false,
    notes text
);

create table if not exists scorecard_results (
    scorecard_result_id text primary key,
    run_id text references artifact_runs(run_id),
    scorecard_profile text not null,
    scorecard_version text,
    profile_scope text,
    is_canonical boolean default false,
    kpi_eligible boolean,
    document_count bigint,
    metric_check_count bigint,
    eligible_metric_count bigint,
    candidate_review_required_count bigint,
    ambiguous_count bigint,
    unsupported_count bigint,
    data_missing_count bigint,
    correct_count bigint,
    wrong_count bigint,
    missing_count bigint,
    abstain_count bigint,
    quarantine_count bigint,
    metric_accuracy double,
    context_accuracy double,
    trust_accuracy double,
    pass_fail_status text,
    acceptance_language text,
    overclaim_guard text,
    source_artifact_path text
);

create table if not exists metric_expectations (
    metric_expectation_id text primary key,
    run_id text references artifact_runs(run_id),
    scorecard_result_id text references scorecard_results(scorecard_result_id),
    document_id text,
    ticker text,
    company text,
    period_type text,
    period_end date,
    metric_name text not null,
    canonical_field text,
    expected_value double,
    expected_value_text text,
    currency text,
    scale text,
    tolerance double,
    expectation_type text,
    evidence_status text,
    support_status text,
    source_pdf_path text,
    source_pdf_sha256 text,
    page_number_pdf integer,
    page_number_appendix integer,
    line_label text,
    column_label text,
    canonical_write boolean default false,
    notes text
);

create table if not exists metric_results (
    metric_result_id text primary key,
    run_id text references artifact_runs(run_id),
    metric_expectation_id text references metric_expectations(metric_expectation_id),
    scorecard_result_id text references scorecard_results(scorecard_result_id),
    document_id text,
    metric_name text not null,
    actual_value double,
    actual_value_text text,
    status text,
    reason text,
    trust_outcome text,
    context_correct boolean,
    context_mismatch_count bigint,
    source_artifact_path text,
    notes text
);

create table if not exists runtime_smokes (
    runtime_smoke_id text primary key,
    run_id text references artifact_runs(run_id),
    runtime_surface text,
    runtime_target text,
    model_label text,
    model_path text,
    endpoint_url text,
    gpu_name text,
    gpu_uuid text,
    prompt_scope text,
    request_count bigint,
    pass_count bigint,
    fail_count bigint,
    min_latency_seconds double,
    max_latency_seconds double,
    avg_latency_seconds double,
    prompt_tokens bigint,
    completion_tokens bigint,
    total_tokens bigint,
    degraded boolean,
    verdict text,
    data_missing_json json,
    source_artifact_path text,
    notes text
);

create table if not exists route_smokes (
    route_smoke_id text primary key,
    run_id text references artifact_runs(run_id),
    route_path text not null,
    route_owner text,
    method text,
    expected_status_code integer,
    actual_status_code integer,
    expected_presence text,
    observed_presence text,
    classification text,
    data_state text,
    degraded boolean,
    data_missing_count bigint,
    pass_fail_status text,
    source_artifact_path text,
    notes text
);

create table if not exists source_label_checks (
    source_label_check_id text primary key,
    run_id text references artifact_runs(run_id),
    surface text,
    query_or_prompt_class text,
    expected_source_label text,
    observed_source_label text,
    source_coverage_status text,
    missing_required_evidence boolean,
    no_hit boolean,
    context_only boolean,
    claim_verified boolean,
    guard_action text,
    pass_fail_status text,
    source_artifact_path text,
    notes text
);

create table if not exists memory_audit_results (
    memory_audit_result_id text primary key,
    run_id text references artifact_runs(run_id),
    db_path text,
    read_only_open_mode text,
    row_total bigint,
    active_row_count bigint,
    duplicate_cluster_count bigint,
    duplicate_row_count bigint,
    source_fanout_cluster_count bigint,
    source_fanout_row_count bigint,
    manual_review_active_count bigint,
    untrusted_memory boolean,
    surfacing_risk text,
    cleanup_readiness text,
    source_artifact_path text,
    notes text
);

create table if not exists news_trace_results (
    news_trace_result_id text primary key,
    run_id text references artifact_runs(run_id),
    ticker text,
    trace_scope text,
    ingestion_status text,
    entity_link_status text,
    sqlite_status text,
    qdrant_status text,
    rag_query_status text,
    backend_chat_status text,
    source_label_status text,
    no_hit boolean,
    missing_required_evidence boolean,
    live_data_access boolean default false,
    data_missing_json json,
    source_artifact_path text,
    notes text
);

create table if not exists dirty_worktree_events (
    dirty_worktree_event_id text primary key,
    run_id text references artifact_runs(run_id),
    branch text,
    head text,
    changed_path text,
    git_status text,
    allowed_by_task_card boolean,
    classification text,
    overlap_risk text,
    action_taken text,
    source_artifact_path text,
    notes text
);

create table if not exists registry_events (
    registry_event_id text primary key,
    run_id text references artifact_runs(run_id),
    job_id text,
    event_type text,
    event_at timestamptz,
    ok boolean,
    active_record_path text,
    registry_scope text,
    active_jobs_json json,
    overlap_issues_json json,
    source_artifact_path text,
    notes text
);

create table if not exists data_missing_items (
    data_missing_id text primary key,
    run_id text references artifact_runs(run_id),
    family_name text,
    missing_class text,
    missing_code text,
    description text not null,
    blocked_by_policy boolean default false,
    blocked_by_environment boolean default false,
    expected_empty_state boolean default false,
    severity text,
    followup_task text,
    source_artifact_path text
);

create table if not exists decisions_and_verdicts (
    decision_id text primary key,
    run_id text references artifact_runs(run_id),
    decision_type text,
    verdict text,
    truth_status text,
    recommendation text,
    confidence text,
    confirmed_facts_json json,
    inferred_facts_json json,
    speculative_claims_json json,
    do_not_do_json json,
    source_artifact_path text,
    notes text
);

create view if not exists v_run_scorecard_summary as
select
    ar.run_id,
    ar.job_id,
    ar.branch,
    ar.head,
    sr.scorecard_profile,
    sr.is_canonical,
    sr.kpi_eligible,
    sr.document_count,
    sr.metric_check_count,
    sr.metric_accuracy,
    sr.context_accuracy,
    sr.trust_accuracy,
    sr.pass_fail_status,
    sr.overclaim_guard
from artifact_runs ar
join scorecard_results sr on sr.run_id = ar.run_id;

create view if not exists v_current_data_missing_by_family as
select
    family_name,
    missing_class,
    missing_code,
    count(*) as item_count
from data_missing_items
group by family_name, missing_class, missing_code;
