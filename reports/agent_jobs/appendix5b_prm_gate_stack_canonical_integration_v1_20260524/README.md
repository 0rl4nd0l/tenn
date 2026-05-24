# Appendix 5B PRM Gate Stack Canonical Integration

Job: `appendix5b_prm_gate_stack_canonical_integration_v1_20260524`

Mode: SAFE EXTENSION / CANONICAL INTEGRATION

## Confirmed Facts

- Target canonical entrypoint `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Target canonical branch before integration: `migration/clean-runtime-baseline-reconstruct-v1`.
- Target canonical HEAD before integration: `e170f6b255ca4229462d4167861775e82ea3df34`.
- Source fast-dev path exists at `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Source fast-dev branch: `migration/clean-runtime-baseline-20260517`.
- Source fast-dev HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Source fast-dev still contains the Appendix 5B service, test, script, docs, and report-local evidence bundle identified by the preservation audit.
- Integration was performed in isolated worktree `/home/l4nd0/tenn-appendix5b-prm-gate-stack-canonical-integration-v1-20260524` on branch `integrate/appendix5b-prm-gate-stack-canonical-integration-v1-20260524`.
- No fast-dev files were edited.
- No runtime topology, Docker, systemd, cron, symlink, mount, DB, Qdrant, news, memory, Cockpit UI, parser routing, dependency, lockfile, model, or GPU/runtime files were changed.
- The preserved source-PDF report symlink was intentionally excluded because it points outside the repo to `/mnt/hdd-cold/tenn/asx-docs/PRM/financial_performance/2026-01-29_quarterly-activities-appendix-5b-cash-flow-report_11faaa3d-4a2c-440f-972f-c2f5630e21ae.pdf`.

## Inferred Facts

- The copied Appendix 5B stack is report-local and evaluation-only because its executable entrypoints write to explicit report paths and validation artifacts record `canonical_write=false`.
- The docs changes are Appendix 5B evaluation-gate documentation only.
- The PRM-inclusive default gate name in `scripts/run_extraction_evaluation_gates.py` needed to be aligned from the stale 10X label to `appendix5b_prm_no_regression`; a focused test now guards that default.

## DATA_MISSING

- Project-specific architecture rule files under `.cursor/rules/` were not present in canonical or fast-dev, so architecture-skill validation could not load those exact rule documents.
- The final integration commit hash cannot be embedded inside this committed report without changing that same commit hash. The final closeout response and `git -C /home/l4nd0/tenn log -1 --oneline` record the immutable hash after commit/fast-forward.
- Final post-fast-forward canonical status is produced after this report is committed; the final closeout response records the exact command output.

## Source And Target

| Item | Value |
| --- | --- |
| Source path | `/home/l4nd0/tenn-fast-dev-storage-v1` |
| Source branch | `migration/clean-runtime-baseline-20260517` |
| Source HEAD | `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` |
| Target path | `/home/l4nd0/tenn` |
| Target resolved path | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Target branch before | `migration/clean-runtime-baseline-reconstruct-v1` |
| Target HEAD before | `e170f6b255ca4229462d4167861775e82ea3df34` |
| Target branch after | `migration/clean-runtime-baseline-reconstruct-v1` after fast-forward |
| Target HEAD after | See final closeout response and `git log -1` |

## Files Copied Or Integrated

Task cards:

- `docs/agent_tasks/appendix5b_prm_gate_stack_canonical_integration_v1_20260524.md`
- `docs/agent_tasks/appendix5b_backend_gate_services_restore_v1_20260517.md`

Appendix 5B services:

- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_parser.py`

Appendix 5B tests:

- `financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_artifacts.py`
- `financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_scorer.py`
- `financial-engine_v2/backend/tests/test_asx_appendix5b_confirmed_label_importer.py`
- `financial-engine_v2/backend/tests/test_asx_appendix5b_label_review_packet.py`
- `financial-engine_v2/backend/tests/test_asx_appendix5b_manifest_builder.py`
- `financial-engine_v2/backend/tests/test_asx_appendix5b_parser.py`

Scripts:

- `scripts/build_appendix5b_manifest_from_docling.py`
- `scripts/build_asx_appendix5b_label_review_packet.py`
- `scripts/import_asx_appendix5b_confirmed_labels.py`
- `scripts/run_appendix5b_candidate_artifacts.py`
- `scripts/run_appendix5b_no_regression_gate.py`
- `scripts/run_extraction_evaluation_gates.py`
- `scripts/score_asx_appendix5b_candidates.py`
- `scripts/test_appendix5b_no_regression_gate.py`
- `scripts/test_extraction_evaluation_gates.py`

Docs:

- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/validation_baseline.md`

## Report Evidence Preserved

Preserved from `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/`:

- `README.md`
- `appendix5b_no_regression_report.json`
- `baseline_artifacts/eqr_q4_fy2026_appendix5b.rerun_artifact.json`
- `baseline_artifacts/gre_asx_june2025_alt.rerun_artifact.json`
- `baseline_artifacts/gre_q4_fy2025_appendix5b.rerun_artifact.json`
- `baseline_artifacts/gre_q_2025-09-30.rerun_artifact.json`
- `baseline_artifacts/pek_asx_july2025_probe.rerun_artifact.json`
- `baseline_artifacts/tenx_artifact.json`
- `confirmed_labels_prm_included.json`
- `diff-check.json`
- `gate_result.json`
- `import_check.txt`
- `prm_artifact.json`
- `prm_docling_runner.out`
- `prm_docling_runner.py`
- `prm_manifest.json`
- `prm_q_2025-12-31.docling.json`
- `prm_q_2025-12-31_source.pdf.docling.json`
- `promotion_decision.json`
- `recurring_eval_report.json`
- `service_inventory.json`
- `status.json`

Note: the extraction-evaluation wrapper re-runs the Appendix 5B gate and writes its expected output to `appendix5b_no_regression_report.json` in this preserved report directory. Relative to the fast-dev source artifact, the only observed content differences after validation were `generated_at` timestamps; gate content and pass/fail data stayed equivalent.

Fresh integration evidence written under `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/`:

- `README.md`
- `status.json`
- `validation.json`
- `diff-check.json`
- `code_review.json`
- `appendix5b_no_regression_report.json`
- `recurring_eval_report.json`

Intentionally ignored:

- `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/prm_q_2025-12-31_source.pdf`: excluded because it is a symlink to cold-storage source data outside the repo.

## Appendix 5B PRM Gate Result

Command:

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_appendix5b_no_regression_gate.py --output reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/appendix5b_no_regression_report.json
```

Result:

- `gate_pass=true`
- `canonical_write=false`
- `failed_checks=[]`
- `candidate_count=81`
- `candidate_unlabelled=20`
- `current_quarter_candidate_count=33`
- `documents_scored=7`
- `document_pass=5`
- `document_fail=0`
- `document_unscored=2`
- `labelled_metric_count=13`
- `trusted_metric_count=13`
- `exact_match_rate=1.0`
- `labelled_metric_coverage=1.0`
- `expected_null_respected=2`

Recurring extraction-evaluation wrapper:

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_extraction_evaluation_gates.py --output reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/recurring_eval_report.json
```

Result:

- `gate_pass=true`
- `canonical_write=false`
- `gate_count=1`
- `failed_gates=[]`
- Gate name: `appendix5b_prm_no_regression`

## canonical_write=false Proof

Validated JSON artifacts:

- `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/appendix5b_no_regression_report.json`: `canonical_write=false`, `gate_pass=true`
- `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/recurring_eval_report.json`: `canonical_write=false`, `gate_pass=true`
- `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/promotion_decision.json`: `canonical_write=false`, `decision=PROMOTED_REPORT_LOCAL_NO_REGRESSION_FLOOR`

Grep proof:

```bash
rg -n "<true canonical-write patterns>" <scoped files and reports>
```

Result after code-review note cleanup: no matches.

## No Parser Routing Proof

Changed-path proof command:

```bash
git diff --cached --name-only | rg '(^financial-engine_v2/backend/app/(api|routes|routers|main|services/(multipass_extraction|method_isolated_extraction|extraction_|asx_document_type|document|process|retrieval|rag|query|router)))|docker|systemd|cockpit-ui|qdrant|memory|news|compose|env' || true
```

Result: no changed parser-routing, runtime, Cockpit UI, data-store, Docker, systemd, compose, or env paths.

Import proof:

- Appendix 5B imports are confined to new Appendix 5B services, tests, scripts, and docs.
- No production parser routing import was added.

## Validation Commands And Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/appendix5b_prm_gate_stack_canonical_integration_v1_20260524.md --write-report`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/appendix5b_prm_gate_stack_canonical_integration_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/appendix5b_prm_gate_stack_canonical_integration_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py heartbeat appendix5b_prm_gate_stack_canonical_integration_v1_20260524`: PASS.
- `python3 -m compileall -q <changed Appendix 5B services/scripts/tests>`: PASS.
- `PYTHONPATH=/home/l4nd0/tenn-appendix5b-prm-gate-stack-canonical-integration-v1-20260524/financial-engine_v2/backend /mnt/sdb2/home/l4nd0/tenn/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_asx_appendix5b_*.py scripts/test_appendix5b_no_regression_gate.py scripts/test_extraction_evaluation_gates.py`: PASS, `48 passed in 0.76s`.
- `python3 -m json.tool <preserved and fresh JSON report artifacts>`: PASS.
- `git diff --check`: PASS.
- Code-reviewer skill review: PASS, no critical findings, warnings, or suggestions.
- Architecture-check skill: DATA_MISSING for project `.cursor/rules/`; scoped path proof found no architecture-sensitive routing/runtime/vector/RAG surfaces changed.
- `task-card check-diff`: run after final staging; result is recorded in `diff-check.json` and final closeout.

Note: system `python3` did not have pytest installed, so focused pytest used the existing Tenn virtualenv at `/mnt/sdb2/home/l4nd0/tenn/.venv/bin/python`. No dependencies were installed.

## Commit

- Commit policy: create one scoped commit with message `feat(evaluation): integrate appendix 5b prm gate stack`.
- Commit hash: see DATA_MISSING note above and final closeout response.

## Final Git Status

- Integration worktree before commit: staged files are within task-card `allowed_files`.
- Canonical pre-fast-forward status contained unrelated pre-existing untracked task cards only; they were not staged, modified, or removed.
- Canonical post-fast-forward status: see final closeout response.

## Registry Status

- Registry overlap check passed before integration.
- Registry claim was refreshed by heartbeat during closeout.
- Registry release returned `ok=true` and removed active record `appendix5b_prm_gate_stack_canonical_integration_v1_20260524.json`.
- Final `list-active` returned `active_jobs=[]`.

## Runtime Topology Rebind

Runtime topology rebind was not performed. The Appendix 5B preservation blocker is addressed by this scoped integration, but any runtime topology rebind remains a separate approval-gated operational task.

## Recommended Next Task

Create a runtime topology rebind readiness task that:

- Re-runs path/branch/HEAD/status and registry preflight.
- Confirms this Appendix 5B integration commit is present in canonical.
- Re-checks fast-dev for any remaining `PRESERVE_AND_INTEGRATE` files outside Appendix 5B.
- Performs no runtime rebind unless explicitly authorized by the new task card.

## Project Memory Save Recommendation

Save a project memory note after closeout: the fast-dev Appendix 5B PRM-inclusive parser/scorer/gate stack was preserved in canonical as a report-local, evaluation-only bundle with `canonical_write=false`, no parser routing, and no runtime topology changes.
