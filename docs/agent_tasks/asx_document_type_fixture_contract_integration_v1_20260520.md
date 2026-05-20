---
job_id: asx_document_type_fixture_contract_integration_v1_20260520
lane: Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
  - docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md
  - docs/asx_document_type_fixture_contract.md
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/ambiguous_appendix_4d_4e_abstain.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/annual_report_basic.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4c_quarterly_cashflow.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4d_half_year_results.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4e_preliminary_final.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_5b_mining_cashflow.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/half_year_report_basic.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/manifest.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/other_asx_announcement_investor_presentation.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/unknown_low_signal.json
  - financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/status.json
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/diff-check.json
mutation_mode: safe_extension
production_data_access: false
output_dir: reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520
approval_required: false
timeout_seconds: 7200
allow_unapproved_safe_extension: true
---

# Task

Integrate the already-validated ASX document-type fixture contract patch from the clean sibling worktree into the active NVMe runtime baseline.

# Source Patch

- Worktree: `/home/l4nd0/tenn-asx-document-type-fixture-contract-v1-20260520`
- Branch: `safe/asx-document-type-fixture-contract-v1-20260520`
- Commit: `5239513b4bbb`
- Commit subject: `feat(financial-truth): add asx document type fixture contract`

# Scope

Integrate only the fixture/schema/test-contract artifacts and report bundle from the source patch:

- source task card;
- ASX document-type fixture contract doc;
- synthetic fixture examples and manifest;
- fixture-only schema tests;
- source report artifacts;
- this integration task card and report.

Do not redesign the fixture contract. Do not add classifier implementation. Do not touch parser routing, extraction, Docling, gold labels, canonical writes, DBs, Qdrant, memory, news, Cockpit, Home, runtime/model/GPU config, or source-label behavior.

# Required Preflight

Run and report:

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry job only if safe.

# Hard Stops

Stop before integration if:

- active registry shows overlapping Financial Truth / parser / extraction / fixture / Evaluation checkpoint work;
- `/home/l4nd0/tenn-runtime` has source-code dirt beyond known task/report artifacts;
- target branch is not `migration/clean-runtime-baseline-reconstruct-v1`;
- target HEAD is not at or after `e006bf86a796`;
- sibling commit `5239513b4bbb` cannot be found;
- integration would touch files outside the allowed list;
- patch conflicts in a way that requires redesign;
- validation cannot be run.

# Integration Method

Before applying, inspect:

- `git show --name-status --oneline --no-renames 5239513b4bbb`
- `git show --stat --oneline --no-renames 5239513b4bbb`

If the commit contains only allowed fixture/doc/test/report/task artifacts, integrate by either cherry-picking the commit if the file set is exactly allowed and conflict-free, or restoring/copying only allowed paths from the sibling commit.

# Patch Invariants

- Fixture/schema/test-contract only.
- Every fixture has `canonical_write=false`.
- Fixture text remains small synthetic/surrogate text.
- Appendix 4C/5B fixtures do not imply income statement metrics.
- Appendix 4D/4E fixtures treat EPS/NTA/dividends as review-only/unsupported context.
- Unknown/ambiguous fixtures abstain.
- No classifier module.
- No parser/extraction imports.
- No production routing.
- No canonical writes.

# Validation

Run:

- `for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`

Do not run extraction jobs, Docling, OCR, comparator tools, Qdrant, news jobs, memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, parser routing, or gold-label/canonical scorecard updates.

# Required Report

Write:

`reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md`

Include confirmed facts, inferred facts, DATA_MISSING, source sibling commit/worktree, files integrated, diff summary, validation commands and exact results, boundary preservation evidence, whether validation matches sibling patch, whether non-report files changed are only allowed fixture/doc/test files, commit hash if committed, final git status, registry release status, and Project Memory save recommendation.
