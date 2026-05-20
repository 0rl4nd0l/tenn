---
job_id: asx_document_type_sidecar_artifact_v1_20260520
lane: Financial Truth
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520
allowed_files:
  - docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md
  - docs/asx_document_type_fixture_contract.md
  - financial-engine_v2/backend/app/services/asx_document_type_classifier.py
  - financial-engine_v2/backend/app/services/asx_document_type_sidecar.py
  - financial-engine_v2/backend/tests/test_asx_document_type_classifier.py
  - financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py
  - financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/
  - scripts/generate_asx_document_type_sidecars.py
  - reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/
  - reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/status.json
---

# ASX Document-Type Sidecar Artifact v1

Add a read-only ASX document-type classifier sidecar artifact format and small
offline generation utility. The sidecar runs the existing pure classifier over
explicit fixture or surrogate inputs and emits metadata-only artifacts with
`canonical_write=false`.

## Scope

- Add `financial-engine_v2/backend/app/services/asx_document_type_sidecar.py`.
- Add `scripts/generate_asx_document_type_sidecars.py`.
- Add focused sidecar tests under
  `financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py`.
- Keep existing fixture-contract and classifier tests passing.
- Add this job's report bundle under
  `reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/`.

## Boundaries

This is a comparator/reporting artifact only. It must not connect the
classifier or sidecar to production extraction, parser routing, Docling, OCR,
prompts, canonical writes, DBs, Qdrant, memory, news, Cockpit, Home,
runtime/model/GPU config, source labels, or financial truth persistence.

Inputs are limited to explicit synthetic fixture or surrogate payloads. The
sidecar must not include full PDF text, infer financial metrics, or write files
unless a caller explicitly writes returned artifacts in tests or scripts.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Financial Truth, parser,
extraction, or ASX classifier work is active.

## Hard Stops

- Active registry shows overlapping Financial Truth, parser, extraction, or
  ASX classifier work.
- Worktree has source-code dirt outside known task/report artifacts.
- Implementation requires production data access.
- Implementation requires running extraction, Docling, OCR, comparator tools,
  Qdrant, news jobs, memory jobs, live Cockpit chat, Home producers, or
  runtime/model/GPU tests.
- Implementation requires importing sidecar or classifier into production
  extraction routing.
- Implementation changes parser routing, prompts, gold labels, canonical
  scorecards, DBs, or financial truth writes.

## Validation

- `for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_document_type_classifier.py financial-engine_v2/backend/app/services/asx_document_type_sidecar.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py scripts/generate_asx_document_type_sidecars.py`
- `python3 scripts/generate_asx_document_type_sidecars.py --fixtures-dir financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier --out-dir /tmp/asx_document_type_sidecars`
- `find /tmp/asx_document_type_sidecars -name '*.json' -print0 | xargs -0 -r jq empty`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`

Do not run extraction jobs, Docling, OCR, comparator tools, Qdrant, news jobs,
memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, parser
routing, or gold-label/canonical scorecard updates.
