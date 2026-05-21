---
job_id: asx_document_type_sidecar_gate_report_v1_20260520
lane: Financial Truth
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520
allowed_files:
  - docs/agent_tasks/asx_document_type_sidecar_gate_report_v1_20260520.md
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/DATA_MISSING.md
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/classifier_gate_results.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/fixture_gate_results.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/gate_summary.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/production_boundary_check.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/sidecar_gate_results.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/status.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/ambiguous_appendix_4d_4e_abstain.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/annual_report_basic.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/appendix_4c_quarterly_cashflow.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/appendix_4d_half_year_results.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/appendix_4e_preliminary_final.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/appendix_5b_mining_cashflow.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/half_year_report_basic.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/other_asx_announcement_investor_presentation.sidecar.json
  - reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars/unknown_low_signal.sidecar.json
---

# ASX Document-Type Sidecar Gate Report v1

Produce a promotion-readiness gate report for the existing ASX
document-type fixture, pure classifier, and sidecar artifact stack. This is an
audit-only evidence packet for offline metadata artifacts.

## Scope

- Validate the existing ASX document-type fixture contract.
- Validate the existing pure classifier behavior against those fixtures.
- Validate the existing sidecar artifact generator.
- Generate report-local sidecars under this job's output directory.
- Perform static import-boundary checks proving production routing is not using
  the classifier or sidecar.
- Write only this task card and report artifacts under this job's report
  directory.

## Boundaries

This gate does not approve parser routing, canonical writes, extraction
integration, Docling integration, OCR, prompts, DB writes, Qdrant writes,
memory jobs, news jobs, Cockpit, Home, runtime/model/GPU changes, source-label
changes, gold-label changes, canonical scorecard changes, or financial truth
persistence.

The sidecar remains an offline metadata artifact with `canonical_write=false`.
Generated sidecars must stay under the report directory or `/tmp`.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_sidecar_gate_report_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_sidecar_gate_report_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Financial Truth, ASX, parser,
extraction, fixture, classifier, or sidecar work is active.

## Hard Stops

- Active registry shows overlapping Financial Truth, ASX, parser, extraction,
  fixture, classifier, or sidecar work.
- Worktree has source-code dirt outside known task/report artifacts.
- The gate requires editing source, tests, fixtures, parser routing, or
  production files.
- The gate requires production data access.
- The gate requires extraction, Docling, OCR, comparator tools, Qdrant, news
  jobs, memory jobs, live Cockpit chat, Home producers, runtime/model/GPU
  tests, parser routing, gold-label/canonical scorecard changes, or DB writes.
- Sidecar generation writes outside the report directory or `/tmp`.

## Validation

- Parse every ASX document-type fixture JSON.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
- `python3 scripts/generate_asx_document_type_sidecars.py --fixtures-dir financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier --out-dir reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars`
- `find reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/generated_sidecars -name '*.json' -print0 | xargs -0 -r jq empty`
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_document_type_classifier.py financial-engine_v2/backend/app/services/asx_document_type_sidecar.py scripts/generate_asx_document_type_sidecars.py`
- `jq empty reports/agent_jobs/asx_document_type_sidecar_gate_report_v1_20260520/*.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_sidecar_gate_report_v1_20260520.md`

Do not run extraction jobs, Docling, OCR, comparator tools, Qdrant, news jobs,
memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, parser
routing, or gold-label/canonical scorecard updates.
