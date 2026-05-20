---
job_id: asx_document_type_pure_classifier_v1_20260520
lane: Financial Truth
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520
allowed_files:
  - docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md
  - financial-engine_v2/backend/app/services/asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/
  - reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/
  - reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/status.json
---

# ASX Document-Type Pure Classifier v1

Implement a pure, deterministic ASX document-type classifier for synthetic
text-surrogate fixture inputs. The classifier returns metadata-only document
classification results and must preserve `canonical_write=false`.

## Scope

- Add `financial-engine_v2/backend/app/services/asx_document_type_classifier.py`.
- Add focused classifier tests under
  `financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`.
- Re-run the existing ASX fixture contract tests.
- Add this job's report bundle under
  `reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/`.

## Boundaries

The classifier is standalone and pure. It must not be imported by production
extraction routing and must not connect to parser routing, Docling, OCR,
prompts, canonical writes, DBs, Qdrant, memory, news, Cockpit, Home, runtime
clients, model/GPU configuration, source labels, or financial truth persistence.

Document-type classification is metadata. Appendix 4C and Appendix 5B cash-flow
forms must not imply revenue, NPAT, net-debt, or income-statement extraction.
Appendix 4D and Appendix 4E metric-like references such as EPS, NTA, and
dividends are review-only unsupported context.

Production data access is false. Inputs are limited to small synthetic
text-surrogate fixture dictionaries.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Financial Truth, parser, extraction,
or ASX fixture work is active.

## Hard Stops

- Active registry shows overlapping Financial Truth, parser, extraction, or
  fixture work.
- Worktree has source-code dirt outside known task/report artifacts.
- The implementation requires production data access.
- The implementation requires extraction jobs, Docling, OCR, comparator tools,
  Qdrant, news jobs, memory jobs, live Cockpit chat, Home producers, or
  runtime/model/GPU tests.
- The implementation requires importing the classifier into production
  extraction routing.
- The implementation changes parser routing, prompts, gold labels, canonical
  scorecards, DBs, or financial truth writes.

## Validation

- `for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_pure_classifier_v1_20260520.md`

Do not run extraction jobs, Docling, OCR, comparator tools, Qdrant, news jobs,
memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, parser
routing, or gold-label/canonical scorecard updates.
