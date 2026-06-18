---
job_id: extraction_hub_current_period_line_binding_v1_20260618
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/README.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/STATE.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/DECISIONS.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/VALIDATION.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/NEXT_GOAL.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/PR_REVIEW.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/git_guard.json
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/status.json
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/validation.json
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/diff-check.json
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/worker_results/implementation/WORKER_RESULT.md
  - reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618/worker_results/review/WORKER_RESULT.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_hub_current_period_line_binding_v1_20260618
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# HUB Current-Period Line Binding

## Objective

Implement the narrow HUB period/source ambiguity fix proven by
`reports/agent_jobs/extraction_hub_period_source_evidence_packet_v1_20260618/`.
When real HUB early text contains both current half-year evidence for
`31 December 2023` and comparative prior half-year evidence for
`31 December 2022`, prefer exact current-period source text before treating the
document as ambiguous.

User approval on 2026-06-18 also permits publishing this bounded local fix as a
draft PR after focused validation remains clean.

## Source Evidence

- Target document:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/HUB/financial_performance/2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_419bcca8-213e-4706-8962-8e3bd8adf091.pdf`
- Evidence packet:
  `/home/l4nd0/tenn-hub-period-source-evidence-packet-v1-20260618/reports/agent_jobs/extraction_hub_period_source_evidence_packet_v1_20260618/`
- Proven source period end:
  `2023-12-31`
- Announcement date:
  `2024-02-20`

## Required Implementation Shape

- Add a focused failing test using real HUB-like early text with:
  - `Appendix 4D - Half-Year Ended 31 December 2023`
  - `Current period: 1 July 2023 to 31 December 2023`
  - comparative/prior half-year evidence for `31 December 2022`
- Implement the smallest deterministic source-bound preference for the
  current-period heading/current-period line.
- Preserve fail-closed behavior for true conflicts, title-date-only evidence,
  label-only evidence, loose dates, and companion disagreement.
- Do not hardcode HUB outside test fixtures.

## Hard Stops

- Do not run extraction, count-24, count-32, random samples, broad extraction,
  backfill, runtime services, full ticker extraction, or broad replay.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, gold labels,
  prompts, runtime/service/model/GPU config, schema, production data, or
  GitHub state beyond pushing this branch and opening/updating one draft PR.
- Do not loosen validators, source mismatch gates, metric ontology, scale
  inference, provenance requirements, or canonical value contracts.
- Do not change unrelated code or reports.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md`
- RED focused test before implementation.
- GREEN focused tests after implementation:
  `PYTHONPATH=financial-engine_v2/backend uv run ... pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -k 'hub or explicit_source_period_end or companion'`
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md`
