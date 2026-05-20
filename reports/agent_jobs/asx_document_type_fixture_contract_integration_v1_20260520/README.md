# ASX Document-Type Fixture Contract Integration

Status: BLOCKED before integration.

## Confirmed Facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Target branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Target HEAD before integration attempt: `e006bf86a796`.
- Task card created and validated: `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`.
- The task card was updated to enumerate exact child fixture and report files because `scripts/agent_job_contract.py check-diff` uses exact path matching.
- Source sibling commit exists in the target repo object database: `5239513b4bbb`.
- Source commit subject: `feat(financial-truth): add asx document type fixture contract`.
- Source commit file set is limited to task card, contract doc, synthetic fixture JSON/manifest files, fixture contract test, and source report artifacts.
- No source commit file is a classifier module, parser route, extraction module, Docling/OCR path, gold label, scorecard, DB/Qdrant/memory/news/Cockpit/Home/runtime config, or source-label behavior file.
- Retry after the first block found the active registry empty, but `check-overlap` still returned `ok=false` because `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md` remains dirty outside this task card's allowlist.

## Inferred Facts

- The source patch appears suitable for a narrow fixture/schema/test-contract integration once the registry and dirty-worktree gates are clear.
- The active `Evaluation` registry job from the first attempt is no longer active.
- The untracked `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md` appears to be stale or separately owned task-card dirt and must not be cleaned, staged, or absorbed by this integration task without explicit authorization.

## DATA_MISSING

- Target-side JSON fixture validation: not run because the source fixtures were not integrated.
- Target-side fixture contract pytest result: not run because the source fixtures/tests were not integrated.
- Target-side `git diff --check`: not run after integration because no integration occurred.
- Target-side `check-diff` result for this integration patch: not run as a passing gate because `check-overlap` failed before registry claim.
- Commit hash for integration commit: DATA_MISSING because no integration commit was created.
- Registry release status for this job: not applicable; this job was never claimed.
- Ownership/status of `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`: DATA_MISSING. It was not inspected or modified by this task beyond `git status` and registry overlap output.

## Source Sibling Commit and Worktree

- Worktree: `/home/l4nd0/tenn-asx-document-type-fixture-contract-v1-20260520`
- Branch: `safe/asx-document-type-fixture-contract-v1-20260520`
- Commit: `5239513b4bbb`

Read-only inspection:

```text
git cat-file -e 5239513b4bbb^{commit} && git rev-parse --short=12 5239513b4bbb
5239513b4bbb
```

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

None. Integration stopped at the registry/overlap gate before cherry-pick or restore.

## Diff Summary

Current task-local changes only:

- Added integration task card.
- Added this blocker report.

Known unrelated dirty file:

- `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`

## Validation Commands and Results

Task card validation before preflight:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
ok=true, issues=[]
```

Preflight:

```text
readlink -f /home/l4nd0/tenn-runtime
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1

git branch --show-current
migration/clean-runtime-baseline-reconstruct-v1

git rev-parse --short=12 HEAD
e006bf86a796

git status --short
?? docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
?? docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
```

Registry:

```text
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
ok=true; active job: strategy_lab_quantdinger_framework_v1_20260520; lane=Evaluation; mutation_mode=audit_only; worktree=/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
ok=false; issue: docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md is dirty outside current task card allowed_files
```

Recheck after waiting:

```text
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
ok=true; active job still present: strategy_lab_quantdinger_framework_v1_20260520

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
ok=false; same dirty task-card issue
```

Retry after user requested `try now`:

```text
python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime
ok=true; active_jobs=[]

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime
ok=false; issue: docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md is dirty outside current task card allowed_files
```

Target-side fixture validation commands were not run because the fixture files were not integrated.

## Boundary Preservation Evidence

- No cherry-pick was started.
- No source paths were restored or copied.
- No classifier module was added.
- No parser routing, extraction, Docling/OCR, gold-label, scorecard, DB/Qdrant/memory/news/Cockpit/Home/runtime/model/GPU/source-label paths were touched.
- The only task-owned non-report file changed in this blocked attempt is the integration task card.
- The source commit read-only file list contains only allowed fixture/doc/test/report/task artifacts.

## Validation Match to Sibling Patch

Not established on the target branch because integration did not occur. The source patch's previously reported sibling validation remains external context only.

## Non-Report File Boundary

Task-owned non-report changes in this blocked attempt:

- `docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md`

Unrelated non-report dirty file present before integration:

- `docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md`

## Commit

No commit created. Commit gate failed before registry claim.

## Final Git Status

Captured before writing this report:

```text
?? docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
?? docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
```

Standard status after this report:

```text
?? docs/agent_tasks/asx_document_type_fixture_contract_integration_v1_20260520.md
?? docs/agent_tasks/strategy_lab_quantdinger_framework_v1_20260520.md
```

Ignored-report proof:

```text
test -f reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md && wc -l reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md
192 reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md

git status --short --ignored=matching reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/README.md
!! reports/agent_jobs/asx_document_type_fixture_contract_integration_v1_20260520/
```

## Registry Release Status

Not released because the job was never claimed. The registry claim was correctly skipped after `check-overlap` returned `ok=false`.

## Project Memory Save Recommendation

Do not save a Project Memory entry yet. Save only after the integration completes or if this exact registry/dirty-task-card blocker repeats and needs a reusable operational note.
