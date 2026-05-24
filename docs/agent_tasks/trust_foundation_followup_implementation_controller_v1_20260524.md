---
job_id: trust_foundation_followup_implementation_controller_v1_20260524
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/trust_foundation_followup_implementation_controller_v1_20260524.md
  - docs/agent_tasks/source_label_semantic_sufficiency_guard_v1_20260524.md
  - docs/agent_tasks/memory_live_inventory_readonly_v1_20260524.md
  - docs/agent_tasks/a2m_news_live_trace_readonly_v1_20260524.md
  - docs/agent_tasks/gold_metric_coverage_eval_spine_normalizer_v1_20260524.md
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/preflight.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/validation.json
  - reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524/diff-check.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/README.md
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/status.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/validation.json
  - reports/agent_jobs/source_label_semantic_sufficiency_guard_v1_20260524/diff-check.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/README.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/status.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/inventory.csv
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/read_only_proof.json
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/memory_live_inventory_readonly_v1_20260524/diff-check.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/trace_artifacts.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/sqlite_inventory.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/qdrant_probe.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/retrieval_trace.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/diff-check.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/README.md
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/status.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/validation.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/scorecards.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/diff-check.json
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/trust_foundation_followup_implementation_controller_v1_20260524
mutation_mode: safe_extension
production_data_access: false
---

# Trust Foundation Follow-up Implementation Controller

## Objective

Coordinate four bounded child jobs: source-label semantic sufficiency, read-only live memory inventory, read-only live A2M news trace, and offline Gold Metric Coverage to Eval Spine normalization.

## Contract Boundaries

- Preserve backend authority, canonical financial truth, memory safety, and source-label provenance.
- Do not write production stores, memory stores, Postgres, Qdrant, news SQLite, parser routes, extraction prompts, Docker, cron, systemd, models, or GPU/runtime topology.
- Implement only where active registry/file risk is low or controlled medium.
- Stop any child on unresolved high collision risk.

## Child Jobs

- `source_label_semantic_sufficiency_guard_v1_20260524`
- `memory_live_inventory_readonly_v1_20260524`
- `a2m_news_live_trace_readonly_v1_20260524`
- `gold_metric_coverage_eval_spine_normalizer_v1_20260524`

## Validation

- Validate all task cards.
- List active registry jobs before and after.
- Claim/release the controller job if overlap checks permit.
- Run focused child validation only.
- Run `git diff --check`.
- Run `check-diff` and report unrelated pre-existing dirt if present.
- Validate all JSON report artifacts.
