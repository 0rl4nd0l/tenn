---
job_id: trust_foundation_next_phase_longrun_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/trust_foundation_next_phase_longrun_v1_20260524.md
  - docs/agent_tasks/recent_news_positive_claim_verified_fixture_v1_20260524.md
  - docs/agent_tasks/memory_fanout_suppression_quarantine_design_v1_20260524.md
  - docs/agent_tasks/a2m_news_projection_path_discovery_v1_20260524.md
  - docs/agent_tasks/eval_spine_normalizer_usage_followup_v1_20260524.md
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/preflight.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/validation.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/diff-check.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/README.md
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/status.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/validation.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/diff-check.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/README.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/status.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/fanout_suppression_design.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.csv
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/validation.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/diff-check.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.csv
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/read_only_checks.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/validation.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/diff-check.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/README.md
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/status.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/scorecards.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/validation.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/diff-check.json
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/README.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Trust Foundation Next Phase Long-run

## Objective

Coordinate four bounded trust-foundation child jobs after `a71a4fbeb447`: recent-news positive source-label regression coverage, memory fanout suppression/quarantine design, A2M news projection path discovery, and Eval Spine normalizer usability.

## Boundaries

- No fake data, fabricated metrics, hidden `DATA_MISSING`, or evidence-label weakening.
- No canonical financial truth, memory, news SQLite, Qdrant, or Postgres writes.
- No parser, extraction prompt, extraction runtime, Docker, cron, systemd, model, GPU, or runtime topology changes.
- Child jobs may edit only their allowlisted files after validation and overlap checks.
- Stop any child job on unresolved HIGH collision risk.

## Child Jobs

- `recent_news_positive_claim_verified_fixture_v1_20260524`
- `memory_fanout_suppression_quarantine_design_v1_20260524`
- `a2m_news_projection_path_discovery_v1_20260524`
- `eval_spine_normalizer_usage_followup_v1_20260524`

## Validation

- Validate controller and child task cards.
- List active registry jobs before and after, and claim/release this controller if overlap checks permit.
- Run focused child validations, JSON artifact validation, `git diff --check`, and controller `check-diff`.
