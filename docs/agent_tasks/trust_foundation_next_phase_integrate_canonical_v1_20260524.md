---
job_id: trust_foundation_next_phase_integrate_canonical_v1_20260524
lane: Evaluation
owner: Codex
supporting_lanes:
  - Provenance
  - Query Orchestration
  - Memory
  - Reporting
  - Financial Truth
mutation_mode: safe_extension
allow_unapproved_safe_extension: true
approval_required: false
production_data_access: false
timeout_seconds: 21600
output_dir: reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524
allowed_files:
  - docs/agent_tasks/trust_foundation_next_phase_integrate_canonical_v1_20260524.md
  - docs/agent_tasks/trust_foundation_next_phase_longrun_v1_20260524.md
  - docs/agent_tasks/recent_news_positive_claim_verified_fixture_v1_20260524.md
  - docs/agent_tasks/memory_fanout_suppression_quarantine_design_v1_20260524.md
  - docs/agent_tasks/a2m_news_projection_path_discovery_v1_20260524.md
  - docs/agent_tasks/eval_spine_normalizer_usage_followup_v1_20260524.md
  - reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/validation.json
  - reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/diff-check.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/README.md
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/status.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/preflight.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/validation.json
  - reports/agent_jobs/trust_foundation_next_phase_longrun_v1_20260524/diff-check.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/README.md
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/status.json
  - reports/agent_jobs/recent_news_positive_claim_verified_fixture_v1_20260524/validation.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/README.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/status.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/fanout_suppression_design.md
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.json
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/candidate_quarantine.csv
  - reports/agent_jobs/memory_fanout_suppression_quarantine_design_v1_20260524/validation.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.csv
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/read_only_checks.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/validation.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/README.md
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/status.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/normalized_manifest.json
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/scorecards.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/metric_expectations.csv
  - reports/agent_jobs/eval_spine_normalizer_usage_followup_v1_20260524/validation.json
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - scripts/reporting/README.md
  - scripts/reporting/gold_metric_coverage_eval_spine_normalizer.py
  - scripts/reporting/test_gold_metric_coverage_eval_spine_normalizer.py
---

# Trust Foundation Next Phase Canonical Integration

## Objective

Integrate source milestone commit `f18fdc2d7f9a766a26ac724122d091bbabbaf0e8`
from `safe/trust-foundation-next-phase-longrun-v1-20260524` into canonical
`/home/l4nd0/tenn` if the merge is narrow, allowed, and validated.

## Boundaries

- Preserve source-label truth, memory safety, A2M `DATA_MISSING` honesty, and
  Eval Spine proof-vs-inventory boundaries.
- Do not write Qdrant, Postgres, news stores, memory stores, production DB
  files, parser or extraction routing, runtime topology, Docker, cron, systemd,
  model, or GPU configuration.
- Do not run live chat synthesis for this integration.
- Do not perform memory cleanup/quarantine or A2M reindex/resync.
- Do not clean, stage, or commit unrelated task-card dirt.
- Stop on broad conflicts, forbidden file mutation, or active-job overlap with
  this task's allowed files.

## Integration Plan

1. Validate this task card and inspect active registry jobs.
2. Cherry-pick source commit `f18fdc2d7f9a766a26ac724122d091bbabbaf0e8` with
   `--no-commit`.
3. Review changed files, forbidden surfaces, semantic evidence boundaries, and
   report-only artifacts before committing.
4. Run focused backend tests, focused Eval Spine reporting tests, Ruff on
   changed Python files, JSON/CSV artifact checks, task-card validation,
   registry overlap/check-diff where supported, and `git diff --check`.
5. Write integration report artifacts and commit only allowed files if
   validation passes.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate` for this card and imported
  child/controller cards.
- `python3 scripts/agent_job_registry.py list-active` and overlap review.
- Focused pytest for source-label and UI-source count coverage.
- Focused pytest for Eval Spine normalizer usage.
- Focused Ruff on changed Python files.
- JSON parse checks for all new report JSON files.
- CSV row/header checks for imported report CSV artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff` for this integration card.

## Deliverables

- Imported source task cards and report artifacts from the source milestone.
- Focused source/test/reporting changes from `f18fdc2d`.
- `reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/README.md`
- `reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/status.json`
- `reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/validation.json`
- `reports/agent_jobs/trust_foundation_next_phase_integrate_canonical_v1_20260524/diff-check.json`
