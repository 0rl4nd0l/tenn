---
job_id: extraction_clv_prose_highlights_metric_fallback_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_clv_prose_highlights_metric_fallback_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_clv_prose_highlights_metric_fallback_v1_20260601/README.md
  - reports/agent_jobs/extraction_clv_prose_highlights_metric_fallback_v1_20260601/status.json
  - reports/agent_jobs/extraction_clv_prose_highlights_metric_fallback_v1_20260601/validation.json
  - reports/agent_jobs/extraction_clv_prose_highlights_metric_fallback_v1_20260601/diff-check.json
mutation_mode: safe_extension
requested_mutation_mode: code_fix
production_data_access: false
approval_required: true
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "Proceed after third-canary retry hard-stopped on CLV with validation_gate:insufficient_metrics:0; source text shows explicit prose-highlight metric facts and no tables."
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_clv_prose_highlights_metric_fallback_v1_20260601
---

# Extraction CLV Prose Highlights Metric Fallback V1

## Objective

Fix the CLV canary blocker where a prose-only results announcement contains
explicit financial highlight facts but `docling_gpu` returns zero tables, causing
Pass 3a to produce zero metrics and the validation gate to fail with
`validation_gate:insufficient_metrics:0`.

## Scope

Allowed implementation:

- Add a conservative deterministic prose-highlights extractor for explicit
  current-period facts in early sections.
- Populate only canonical `METRIC_FIELDS` values that are directly supported by
  source text.
- Preserve provenance and row references for every prose-derived metric.
- Keep validation gates unchanged.
- Add focused unit coverage for CLV-style prose highlights.

Not allowed:

- Mapping EBITDA to EBIT.
- Using guidance values as current-period revenue.
- Inferring missing metrics.
- Lowering metric-count, confidence, period, unit, or source mismatch gates.
- Runtime extraction, backfill, direct SQL mutation, source PDF mutation, schema
  migration, Qdrant/news/memory writes, Cockpit UI, or GitHub mutation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION.

Intended files: task card, `multipass_extraction.py`, focused multipass tests,
STATE note, and report bundle.

Contested surfaces touched: none from the repo contested-surface list.

Collision risk: HIGH because the change touches canonical financial-truth
metric extraction. Proceed only with an active registry claim and focused tests.

Decision: proceed after validation, overlap check, and registry claim.

## Contract Check

Target system layers: Metric Extraction and Storage preparation.

Relevant contract rules: backend is sole authority; metric extraction may only
use explicit source values; normalization may convert explicit units but must
not infer, substitute, fabricate, or lower validation gates.

What must not change: parser routing, LLM prompts, schema/migrations, source
PDFs, canary runtime state, scorecard gates, storage metric whitelist, and
existing validation gate thresholds.

Why safe: the extractor will only read explicit current-period prose values from
source text, convert explicit units deterministically, preserve per-metric
provenance, and leave all fail-closed gates intact.

GPU process check required: no. This is code and unit-test work only.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_clv_prose_highlights_metric_fallback_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_clv_prose_highlights_metric_fallback_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_clv_prose_highlights_metric_fallback_v1_20260601.md --repo-root .`
- Focused multipass pytest for prose highlights.
- Broader relevant multipass/pipeline guard tests as needed.
- Targeted Ruff.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_clv_prose_highlights_metric_fallback_v1_20260601.md --repo-root .`
- Registry release and final list-active.
