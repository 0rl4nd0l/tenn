# ASX Document-Type Fixture Contract Integration

Status: READY FOR CHECKPOINT COMMIT.

## Confirmed Facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Preflight HEAD before integration: `69ac899b2b2c`.
- Previous blocker chain was resolved by `69ac899b2b2c milestone(evaluation): checkpoint loose task-card blockers`.
- Task card: `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`.
- Task-card validation: `ok=true`.
- Pre-claim registry state: `active_jobs=[]`.
- Pre-claim overlap check for this ASX task: `ok=true`.
- Registry claim succeeded for `asx_document_type_fixture_contract_integration_v1_20260520`.
- Registry release succeeded before the checkpoint commit so the released `status.json` could be preserved and the final worktree could end clean.
- The task card was updated to allow the exact registry-created status artifact: `reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/status.json`.
- Source sibling worktree: `/home/l4nd0/tenn-asx-document-type-fixture-contract-v1-20260520`.
- Source branch: `safe/asx-document-type-fixture-contract-v1-20260520`.
- Source commit: `5239513b4bbb`.
- Source commit subject: `feat(financial-truth): add asx document type fixture contract`.
- Integration method: `git cherry-pick --no-commit 5239513b4bbb`.
- Cherry-pick result: applied cleanly with no conflicts.
- No classifier module was added.
- No parser routing, extraction, Docling/OCR, gold-label, canonical scorecard, DB, Qdrant, memory, news, Cockpit, Home, runtime/model/GPU config, or source-label behavior file was touched.

## Inferred Facts

- The integrated source patch is fixture/schema/test-contract only.
- The target validation matches the sibling validation result for the focused test: `9 passed, 1 warning`.
- The only non-report files changed are task cards, the ASX contract doc, synthetic fixture JSON/manifest files, and the fixture contract test.

## DATA_MISSING

- Production classifier behavior: intentionally DATA_MISSING because no classifier module was added.
- Parser/extraction runtime behavior: intentionally DATA_MISSING because parser routing and extraction were not run or changed.
- Commit hash: DATA_PENDING at report write time; final assistant closeout records the committed hash.

## Source Commit Inspection

```text
git show --name-status --oneline --no-renames 5239513b4bbb
5239513b feat(financial-truth): add asx document type fixture contract
A docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md
A docs/asx_document_type_fixture_contract.md
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/ambiguous_appendix_4d_4e_abstain.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/annual_report_basic.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4c_quarterly_cashflow.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4d_half_year_results.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4e_preliminary_final.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_5b_mining_cashflow.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/half_year_report_basic.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/manifest.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/other_asx_announcement_investor_presentation.json
A financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/unknown_low_signal.json
A financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py
A reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/README.md
A reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/diff-check.json
```

```text
git show --stat --oneline --no-renames 5239513b4bbb
15 files changed, 1208 insertions(+)
```

## Files Integrated

- `docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`
- `docs/asx_document_type_fixture_contract.md`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/ambiguous_appendix_4d_4e_abstain.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/annual_report_basic.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4c_quarterly_cashflow.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4d_half_year_results.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4e_preliminary_final.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_5b_mining_cashflow.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/half_year_report_basic.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/manifest.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/other_asx_announcement_investor_presentation.json`
- `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/unknown_low_signal.json`
- `financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py`
- `reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/README.md`
- `reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/diff-check.json`

Integration task artifacts changed:

- `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
- `reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md`
- `reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/status.json`

## Diff Summary

Current source patch staged by cherry-pick:

```text
15 files changed, 1208 insertions(+)
```

Expected final integration diff also includes this integration task-card metadata/report/status update.

## Validation Commands and Results

Task-card validation:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
ok=true; issues=[]
```

Registry:

```text
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
ok=true; active_jobs=[]

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
ok=true; issues=[]

python3 scripts/agent_job_registry.py claim docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
ok=true; status_path=reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/status.json
```

Fixture JSON parse:

```text
for path in financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/*.json; do python3 -m json.tool "$path" >/dev/null || exit 1; done
exit=0; no output
```

Fixture contract tests:

```text
uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q
.........                                                                [100%]
9 passed, 1 warning in 0.03s
```

Whitespace:

```text
git diff --check
exit=0; no output
```

Remaining staged validation commands are run after this report is staged:

- `git diff --cached --name-status`
- `git diff --cached --stat`
- staged allowlist leak check
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`
- `git diff --cached --check`

## Boundary Preservation Evidence

- No source path outside the ASX fixture contract source commit file list was integrated.
- `rg` over the integrated contract/test/fixture paths shows the no-routing/no-extraction/no-canonical-write boundary text.
- Every fixture and the manifest use `canonical_write=false`; the focused test includes `test_canonical_write_is_false_for_every_fixture_and_manifest`.
- Appendix 4C and 5B fixtures include notes that classification must not imply revenue, NPAT, net debt, or canonical metric extraction.
- Appendix 4D and 4E handling remains review-only/unsupported for EPS/NTA/dividends through fixture expectations and contract prose.
- Unknown/ambiguous fixtures abstain.
- No production validation, extraction job, Docling/OCR, Qdrant, news, memory, Cockpit, Home, runtime/model/GPU, parser routing, or gold-label/canonical scorecard update was run.

## Validation Match to Sibling Patch

Sibling reported validation:

- JSON parse over fixture JSON files: passed.
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`: `9 passed, 1 warning`.

Target validation:

- JSON parse over fixture JSON files: passed.
- Same pytest command: `9 passed, 1 warning`.

## Non-Report File Boundary

Non-report files changed by this integration are limited to:

- ASX integration task card metadata;
- source task card;
- ASX fixture contract doc;
- fixture JSON/manifest files;
- fixture contract test.

No source/runtime/data/config files are present in the changed file set.

## Registry Release Status

Registry release:

```text
python3 scripts/agent_job_registry.py release asx_document_type_fixture_contract_integration_v1_20260520 --repo-root /home/l4nd0/tenn-runtime
ok=true
removed_active_record=/mnt/hdd-data/home/l4nd0/tenn/.git/tenn-agent-registry/active/asx_document_type_fixture_contract_integration_v1_20260520.json
status_path=reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/status.json
```

Release was performed before commit so the released status artifact could be included in the checkpoint. Final `list-active` is captured after commit.

## Project Memory Save Recommendation

No Project Memory save is needed for the fixture contract itself. A memory update may be useful only if repeated blocked integration runs make the loose-task-card checkpoint pattern worth preserving.
