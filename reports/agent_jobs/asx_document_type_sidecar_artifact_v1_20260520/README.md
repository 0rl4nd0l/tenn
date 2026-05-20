# ASX Document-Type Sidecar Artifact v1 Report

## Confirmed Facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch at implementation: `migration/clean-runtime-baseline-reconstruct-v1`.
- Baseline HEAD at preflight: `a56911ac8b81`.
- The worktree was clean before creating this task card.
- Task-card validation passed for `docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`.
- Registry overlap was clean before claim; no active jobs were listed at claim time.
- Registry was claimed and later released for `asx_document_type_sidecar_artifact_v1_20260520`.
- A separate active Evaluation job appeared later and did not overlap this Financial Truth sidecar task.
- The sidecar module imports only standard-library modules plus `app.services.asx_document_type_classifier`.
- The CLI script imports the sidecar module and does not import backend app startup or `app.routes`.
- Generated sidecar JSON files were written only to `/tmp/asx_document_type_sidecars` during smoke validation.

## Inferred Facts

- The sidecar is suitable as a comparator/reporting artifact because it returns only classifier metadata and caller-supplied identifiers.
- The sidecar does not create a production extraction path because no route, parser, worker, pipeline, Docling, or extraction files import it.
- The sidecar checksum is deterministic for a given fixture or explicit surrogate payload because it hashes canonical JSON for `fixture_id`, `document_id`, `ticker`, and `source_text_surrogate`.

## DATA_MISSING

- Production corpus behavior is intentionally not checked; production data access is false for this job.
- `.cursor/rules/` architecture rule files expected by the architecture-check skill were not present in this checkout. Fallback architecture docs checked: `docs/architecture/06_embeddings_and_vector_store.md`, `docs/architecture/10_failure_model.md`, and `docs/architecture/17_agentic_chat_architecture.md`.
- The final commit hash cannot be self-recorded inside this pre-commit report. It must be read from Git after commit.

## Files Added Or Modified

- Added `docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`.
- Added `financial-engine_v2/backend/app/services/asx_document_type_sidecar.py`.
- Added `financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py`.
- Added `scripts/generate_asx_document_type_sidecars.py`.
- Added `reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/README.md`.
- Generated report metadata: `reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/status.json` and `reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/diff-check.json`.

## Sidecar Artifact Schema Summary

The sidecar emits a dictionary with:

- `artifact_type`: `asx_document_type_sidecar_v1`
- `schema_version`: `1`
- `document_id`
- `fixture_id` when fixture input provides it
- `ticker`
- `source`
- `classifier_version`: `asx_document_type_classifier_v1`
- `document_type`
- `confidence_band`
- `abstain`
- `canonical_write`: always `false`
- `positive_evidence`
- `negative_evidence`
- `abstain_reasons`
- `warnings`
- `generated_at`
- `input_checksum`

The artifact does not include `source_text_surrogate`, full PDF text, page text, or metric values.

## Script Behavior Summary

- `scripts/generate_asx_document_type_sidecars.py` requires `--fixtures-dir`.
- The fixture directory must contain `manifest.json` with contract `asx_document_type_fixture_contract_v1` and `canonical_write=false`.
- `--out-dir` defaults to `reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/sidecars/`.
- The script writes one `<fixture_id>.sidecar.json` per fixture.
- The script validates every generated artifact has `canonical_write=false`.
- The script refuses missing fixture directories, non-fixture directories, unsafe fixture names, and output paths inside the fixture directory.

## Supported Document Types

- `annual_report`
- `half_year_report`
- `appendix_4c`
- `appendix_4d`
- `appendix_4e`
- `appendix_5b`
- `other_asx_announcement`
- `unknown_or_abstain`

## Abstain Behavior

- Low-signal fixtures return `document_type=unknown_or_abstain`, `confidence_band=abstain`, `abstain=true`, non-empty `abstain_reasons`, and no positive evidence.
- Conflicting Appendix form labels return `unknown_or_abstain` with non-empty `abstain_reasons` and negative evidence.
- Non-abstain fixtures include positive evidence and empty `abstain_reasons`.

## Safety Boundary Confirmation

- Production data access: no.
- Parser routing changed: no.
- Extraction behavior changed: no.
- Docling/OCR/comparator/Qdrant/news/memory/Cockpit/Home/runtime/model/GPU jobs run: no.
- Production routing imports sidecar: no.
- Canonical writes performed or authorized: no.
- Gold labels or canonical scorecards changed: no.
- `canonical_write` is always false: yes.
- Generated sidecars committed: no.

## Validation Commands And Results

- `readlink -f /home/l4nd0/tenn-runtime`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git branch --show-current`: `migration/clean-runtime-baseline-reconstruct-v1`
- `git rev-parse --short=12 HEAD`: `a56911ac8b81`
- `git status --short`: clean at preflight.
- `git show --stat --oneline --no-renames HEAD`: `a56911ac feat(financial-truth): add pure asx document type classifier`, 5 files changed, 881 insertions.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`: `ok=true`.
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`: `active_jobs=[]` at claim-time preflight.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`: `ok=true`.
- Fixture JSON parse loop: passed.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`: `9 passed, 1 warning`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_classifier.py -q`: `9 passed, 1 warning`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`: `11 passed, 1 warning`.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`: `29 passed, 1 warning`.
- Initial exact compileall was blocked by a pre-existing root-owned `financial-engine_v2/backend/app/services/__pycache__`.
- `PYTHONPYCACHEPREFIX=/tmp/tenn_compile_pycache python3 -m compileall ...`: passed as an isolation proof.
- After renaming the stale root-owned cache to ignored `financial-engine_v2/backend/app/services/__pycache__.pyc`, `python3 -m compileall financial-engine_v2/backend/app/services/asx_document_type_classifier.py financial-engine_v2/backend/app/services/asx_document_type_sidecar.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py scripts/generate_asx_document_type_sidecars.py`: passed.
- `python3 scripts/generate_asx_document_type_sidecars.py --fixtures-dir financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier --out-dir /tmp/asx_document_type_sidecars`: `ok=true`, `sidecar_count=9`.
- `find /tmp/asx_document_type_sidecars -name '*.json' -print0 | xargs -0 -r jq empty`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md`: passed before report write; final check rerun after staging report artifacts.

## Final Git Status

Pre-commit status after force-adding the allowed report artifacts:

```text
A  docs/agent_tasks/asx_document_type_sidecar_artifact_v1_20260520.md
A  financial-engine_v2/backend/app/services/asx_document_type_sidecar.py
A  financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py
A  reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/README.md
A  reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/diff-check.json
A  reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/status.json
A  scripts/generate_asx_document_type_sidecars.py
```

## Registry Release Status

- Claimed: yes.
- Released: yes.
- Release command result: `ok=true`.
- Removed active record: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/active/asx_document_type_sidecar_artifact_v1_20260520.json`.
- Final `list-active` no longer includes this job; it only showed the unrelated Evaluation job `strategy_lab_quantdinger_phase1_sandbox_v1_20260520`.

## Commit Hash If Committed

DATA_MISSING in this report at write time. Read `git rev-parse --short=12 HEAD` after commit.

## Project Memory Save Recommendation

Save this pattern only if future ASX metadata comparator work continues: pure classifier sidecars should remain fixture/surrogate-only, emit `canonical_write=false`, never import production routing, and validate route absence plus generated temp artifacts before commit.
