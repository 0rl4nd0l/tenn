# Draft Child Task Card

This is a draft only. It was not claimed or implemented by this audit.

```markdown
---
job_id: confirmed_metric_scoring_gap_safe_extension_v1_20260524
title: Confirmed Metric Scoring Gap Safe Extension v1
owner: Codex
lane: Evaluation
primary_lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
mutation_mode: safe_extension
approval_required: false
production_data_access: false
timeout_seconds: 14400
output_dir: reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524
allowed_files:
  - docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md
  - financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/README.md
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/status.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/confirmed_metric_scoring_gap_report.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/validation.json
  - reports/agent_jobs/confirmed_metric_scoring_gap_safe_extension_v1_20260524/diff-check.json
allow_audit_code_changes: true
---

# Confirmed Metric Scoring Gap Safe Extension v1

Produce or normalize a confirmed metric coverage scoring-gap artifact now that
source-PDF route resolution is proven for all 15 fixture source groups and all
73 scorecard-scored-ready rows.

## Scope

- Revalidate current branch, HEAD, dirty state, worktrees, registry, and task
  card before implementation.
- Preserve profile labels: `canonical_core`, `expanded_required`, and
  `confirmed_metric_coverage` must remain separate.
- Use confirmed metric coverage fixtures from
  `financial-engine_v2/backend/tests/eval_fixtures`.
- Treat the 73 `CONFIRMED_SOURCE_EVIDENCED` / scorecard-scored-ready rows as
  the only denominator eligible for this task.
- Keep 70 candidate rows excluded.
- Keep 3 ambiguous rows excluded.
- If reporting source-PDF status, distinguish project-root fixture existence
  from source-route openability through `/data/asx/docs`.

## Boundaries

- Do not write canonical financial truth.
- Do not mutate DB, Qdrant, SQLite, Postgres, news stores, Tenn memory,
  company memory, market memory, thesis memory, or production data.
- Do not copy, download, move, import, normalize, or regenerate source PDFs.
- Do not mutate fixture labels.
- Do not weaken source-route allowlists.
- Do not edit parser routing, extraction routing, Docling config, or extraction
  prompts.
- Do not run production extraction, ingestion, backfill, reindex, or resync.
- Do not claim broad metric extraction accuracy.
- Do not combine profile denominators.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md`
- Focused pytest for changed confirmed metric coverage service/API tests.
- `python3 -m json.tool` for generated JSON artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/confirmed_metric_scoring_gap_safe_extension_v1_20260524.md`

## Hard Stops

- Stop if source-route openability no longer resolves the 15 fixture PDFs.
- Stop if scoring would require candidate or ambiguous label promotion.
- Stop if extracted-payload generation would require production extraction or
  production data access.
- Stop if any change touches parser routing, canonical truth, memory stores,
  DB/Qdrant, source-route allowlists, or source PDF files.
```
