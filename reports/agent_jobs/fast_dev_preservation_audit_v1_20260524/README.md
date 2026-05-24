# Fast-dev Preservation Audit

Job: `fast_dev_preservation_audit_v1_20260524`

Mode: audit only / preservation plan

## Confirmed Facts

- Canonical entrypoint `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Canonical HEAD: `e170f6b255ca4229462d4167861775e82ea3df34`.
- Fast-dev path exists at `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Fast-dev branch: `migration/clean-runtime-baseline-20260517`.
- Fast-dev HEAD: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- Fast-dev has 4 tracked modifications and 32 non-ignored untracked files.
- Fast-dev has ignored local artifacts including `cockpit-ui/node_modules`, `cockpit-ui/.next`, `.pytest_cache`, `.ruff_cache`, `financial-engine_v2/data/*`, `financial-engine_v2/reports/*`, and `reports/*`.
- `git merge-base fast-dev HEAD canonical HEAD` is `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`.
- `git rev-list --left-right --count fast-dev...canonical` by HEAD is `0 33`.
- The literal worktree-path rev-list form failed because Git did not treat `/home/l4nd0/tenn-fast-dev-storage-v1.../home/l4nd0/tenn` as revisions.
- Registry `list-active` in canonical returned no active jobs at preflight.
- Registry `check-overlap` failed only because canonical already had unrelated untracked task cards outside this task card allowlist.
- No registry claim was acquired because the overlap precheck was not clean.

## Inferred Facts

- Fast-dev contains no unique committed work ahead of canonical.
- The important fast-dev risk is uncommitted work, especially the Appendix 5B PRM-inclusive evaluation stack and ignored report evidence.
- Current canonical does not contain the Appendix 5B parser/scorer/importer/gate files at their fast-dev paths.
- Many Appendix 5B files in fast-dev exactly match already committed safe-branch blobs, but those blobs are not present in current canonical.
- The PRM-inclusive gate wrapper files are more advanced than the latest 10X/recurring safe-branch versions and appear to be fast-dev-only uncommitted work.
- The Cockpit `allowedDevOrigins` change is local runtime/developer-access configuration and should not be integrated as a hard-coded host IP without a separate config design.

## DATA_MISSING

- I did not open SQLite databases, memory stores, Qdrant, production data, or runtime services.
- I did not verify the current live Docker/systemd/Cockpit process CWD during this preservation audit; that belongs to the runtime topology rebind task.
- I did not checksum every ignored report/data artifact recursively. I inspected ignored artifact paths and key Appendix 5B report metadata only.
- I did not decide discard for any file. Discard still requires explicit user approval.

## Relationship

| Item | Result |
| --- | --- |
| Unique fast-dev commits not in canonical | No |
| Fast-dev ahead of canonical | 0 commits |
| Canonical ahead of fast-dev | 33 commits |
| Merge base | `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0` |
| Runtime rebind status | Still blocked until preservation decisions below are executed |

## Tracked Modification Table

| Path | Lane | Summary | Classification | Recommended action |
| --- | --- | --- | --- | --- |
| `cockpit-ui/next-env.d.ts` | Reporting / Runtime-Ops | Generated Next type reference changed from `./.next/types/routes.d.ts` to `./.next/dev/types/routes.d.ts`. | GENERATED_OR_LOCAL_NOISE | Do not integrate. Let Next regenerate in the target checkout. |
| `cockpit-ui/next.config.mjs` | Reporting / Runtime-Ops | Adds `allowedDevOrigins: ['100.122.176.103', 'localhost', '127.0.0.1']`. | PRESERVE_AS_ARCHIVE_ONLY | Preserve the need before rebind, but do not commit the hard-coded host IP as-is. Create a Runtime/Ops follow-up if LAN/Tailscale dev access is still required. |
| `docs/architecture/12_evaluation_and_drift_monitoring.md` | Evaluation | Documents the Appendix 5B report-local no-regression gate and PRM-inclusive floor. | PRESERVE_AND_INTEGRATE | Integrate only with the Appendix 5B gate stack and report evidence. |
| `docs/validation_baseline.md` | Evaluation | Adds `python scripts/run_extraction_evaluation_gates.py` and the recurring extraction gate to the passing gate set. | PRESERVE_AND_INTEGRATE | Integrate with the gate scripts; do not land this doc without the runnable gate. |

## Untracked File Table

| Path | Lane | Summary | Exists in canonical? | Classification | Recommended action |
| --- | --- | --- | --- | --- | --- |
| `docs/agent_tasks/appendix5b_backend_gate_services_restore_v1_20260517.md` | Evaluation | Completed task card for restoring Appendix 5B backend services and PRM floor. | No | PRESERVE_AND_INTEGRATE | Preserve with the Appendix 5B integration bundle. |
| `docs/agent_tasks/appendix5b_gate_stack_prm_promotion_v1_20260517.md` | Evaluation | Earlier blocked PRM promotion task card, superseded by backend restore. | No | PRESERVE_AS_ARCHIVE_ONLY | Archive as provenance; do not use as the integration source of truth. |
| `docs/agent_tasks/codex_automation_inventory_v1.md` | Repo Hygiene | Audit-only automation inventory card. | No | PRESERVE_AS_ARCHIVE_ONLY | Preserve only if automation audit history is needed. |
| `docs/agent_tasks/codex_automation_ownership_reconciliation_v1.md` | Repo Hygiene | Audit-only automation ownership reconciliation card. | No | PRESERVE_AS_ARCHIVE_ONLY | Preserve with automation reports if desired. |
| `docs/agent_tasks/m40_8001_conservative_validation_v1_20260517.md` | Runtime/Ops | M40 conservative validation card; canonical has later M40 wrapper/runtime evidence but not this card. | No exact file | SUPERSEDED_BY_CANONICAL | Do not integrate by default; archive only if runtime history needs the exact task card. |
| `docs/agent_tasks/nvme_clean_runtime_baseline_integration_v1_20260517.md` | Repo Hygiene / Runtime-Ops | Older NVMe baseline integration card. | No | SUPERSEDED_BY_CANONICAL | Current canonical is a later clean baseline; no direct integration. |
| `docs/agent_tasks/nvme_partial_baseline_checkpoint_v1_20260517.md` | Repo Hygiene / Runtime-Ops | Older partial baseline checkpoint card. | No | SUPERSEDED_BY_CANONICAL | Archive only if needed for migration history. |
| `docs/agent_tasks/nvme_required_commit_finish_v1_20260517.md` | Repo Hygiene / Runtime-Ops | Older required-commit finish card. | No | SUPERSEDED_BY_CANONICAL | Do not integrate into canonical. |
| `docs/agent_tasks/nvme_required_conflict_resolution_v1_20260517.md` | Repo Hygiene / Runtime-Ops | Older required-conflict card. | No | SUPERSEDED_BY_CANONICAL | Current canonical has later migration state; no direct integration. |
| `docs/agent_tasks/sloppy_fix_ownership_audit_v1.md` | Repo Hygiene | Audit-only write-capable GitHub Actions ownership card. | No | PRESERVE_AS_ARCHIVE_ONLY | Archive with automation audit reports if desired. |
| `docs/agent_tasks/strategy_lab_quantdinger_fit_audit_v1_20260520.md` | Evaluation | Phase 0 QuantDinger fit audit card. | No | SUPERSEDED_BY_CANONICAL | Later canonical Strategy Lab phase3g material supersedes it; archive only if historical source inventory is needed. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py` | Evaluation / Financial Truth | Builds Appendix 5B candidate artifacts from manifests; exact blob matches safe branch `6411ccb5`. | No | PRESERVE_AND_INTEGRATE | Integrate with focused tests. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py` | Evaluation / Financial Truth | Scores candidate artifacts against report-local labels; exact blob matches safe branch `9996010f`. | No | PRESERVE_AND_INTEGRATE | Integrate with focused tests. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py` | Evaluation / Financial Truth | Imports confirmed Appendix 5B labels; exact blob matches safe branch `3c5e21d5`. | No | PRESERVE_AND_INTEGRATE | Integrate with report-local boundary checks. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py` | Evaluation / Financial Truth | Builds label review packets; exact blob matches safe branch `e850ff87`. | No | PRESERVE_AND_INTEGRATE | Integrate with tests. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py` | Evaluation | Builds manifests from structured Docling/gold inputs; exact blob matches safe branch `03f6e11d`. | No | PRESERVE_AND_INTEGRATE | Integrate with tests. |
| `financial-engine_v2/backend/app/services/asx_appendix5b_parser.py` | Financial Truth / Evaluation | Deterministic Appendix 5B parser; exact blob matches safe branch `ca00e214`. | No | PRESERVE_AND_INTEGRATE | Integrate only under a Financial Truth/Evaluation task with regression tests. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_artifacts.py` | Evaluation | Focused candidate artifact tests; exact blob matches safe branch `ca00e214`. | No | PRESERVE_AND_INTEGRATE | Integrate with service files. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_candidate_scorer.py` | Evaluation | Focused scorer tests; exact blob matches safe branch `9996010f`. | No | PRESERVE_AND_INTEGRATE | Integrate with scorer. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_confirmed_label_importer.py` | Evaluation | Focused label importer tests; exact blob matches safe branch `3c5e21d5`. | No | PRESERVE_AND_INTEGRATE | Integrate with importer. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_label_review_packet.py` | Evaluation | Focused review packet tests; exact blob matches safe branch `e850ff87`. | No | PRESERVE_AND_INTEGRATE | Integrate with review packet builder. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_manifest_builder.py` | Evaluation | Focused manifest builder tests; exact blob matches safe branch `03f6e11d`. | No | PRESERVE_AND_INTEGRATE | Integrate with manifest builder. |
| `financial-engine_v2/backend/tests/test_asx_appendix5b_parser.py` | Financial Truth / Evaluation | Parser regression tests; exact blob matches safe branch `ca00e214`. | No | PRESERVE_AND_INTEGRATE | Integrate with parser. |
| `scripts/build_appendix5b_manifest_from_docling.py` | Evaluation | CLI for manifest building; exact blob matches safe branch `03f6e11d`. | No | PRESERVE_AND_INTEGRATE | Integrate with service stack. |
| `scripts/build_asx_appendix5b_label_review_packet.py` | Evaluation | CLI for review packet generation; exact blob matches safe branch `e850ff87`. | No | PRESERVE_AND_INTEGRATE | Integrate with review packet service. |
| `scripts/import_asx_appendix5b_confirmed_labels.py` | Evaluation | CLI for confirmed label import; exact blob matches safe branch `4123b4d8`. | No | PRESERVE_AND_INTEGRATE | Integrate with importer. |
| `scripts/run_appendix5b_candidate_artifacts.py` | Evaluation | CLI for candidate artifact generation; exact blob matches safe branch `6411ccb5`. | No | PRESERVE_AND_INTEGRATE | Integrate with candidate artifact service. |
| `scripts/run_appendix5b_no_regression_gate.py` | Evaluation | PRM-inclusive no-regression gate wrapper; differs from latest safe branch `ae2dfd81` by moving from 10X to PRM-inclusive floor. | No | PRESERVE_AND_INTEGRATE | High priority preservation. Integrate with PRM report artifacts and tests. |
| `scripts/run_extraction_evaluation_gates.py` | Evaluation | Recurring wrapper output path retargeted to PRM backend-restore report bundle; differs from latest safe branch `5d08ee34`. | No | PRESERVE_AND_INTEGRATE | Integrate with the PRM gate wrapper. |
| `scripts/score_asx_appendix5b_candidates.py` | Evaluation | CLI for scoring candidates; exact blob matches safe branch `9996010f`. | No | PRESERVE_AND_INTEGRATE | Integrate with scorer. |
| `scripts/test_appendix5b_no_regression_gate.py` | Evaluation | PRM-inclusive gate tests; differs from latest safe branch by raising floor from 4/12 to 5/13. | No | PRESERVE_AND_INTEGRATE | Integrate with gate wrapper. |
| `scripts/test_extraction_evaluation_gates.py` | Evaluation | Recurring wrapper tests; exact blob matches safe branch `5d08ee34`. | No | PRESERVE_AND_INTEGRATE | Integrate with recurring wrapper. |

## Appendix 5B / Evaluation Findings

- The Appendix 5B service/test/script stack is production/evaluation-relevant and absent from canonical.
- The report bundle `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/` is ignored by Git but contains important preservation evidence:
  - `README.md` says PRM Dec 2025 was promoted into the report-local no-regression floor after the PRM-inclusive gate passed.
  - `promotion_decision.json` records decision `PROMOTED_REPORT_LOCAL_NO_REGRESSION_FLOOR`.
  - `gate_result.json` and `appendix5b_no_regression_report.json` record `gate_pass: true`, `documents_scored: 7`, `document_pass: 5`, `labelled_metric_count: 13`, `trusted_metric_count: 13`, `exact_match_rate: 1.0`, and `canonical_write: false`.
  - `service_inventory.json` lists the restored service files, focused tests, and scripts.
- This evidence must be preserved before retiring or rebinding away from fast-dev.
- Do not integrate only the docs or wrapper scripts. The docs, gate wrappers, parser/scorer services, tests, and PRM report artifacts form one coherent unit.

## Cockpit UI Config Findings

- `cockpit-ui/next.config.mjs` contains a hard-coded local allowed-dev origin: `100.122.176.103`.
- This likely supported phone/LAN/Tailscale access to the dev UI.
- It is not safe to commit as-is to canonical because it is host-specific.
- If the rebind still needs LAN dev access, make it a config/env-driven Runtime/Ops follow-up.
- `cockpit-ui/next-env.d.ts` is generated and should not be preserved as source.

## Generated / Local Noise Findings

| Path family | Classification | Recommended action |
| --- | --- | --- |
| `cockpit-ui/next-env.d.ts` | GENERATED_OR_LOCAL_NOISE | Do not integrate. |
| `cockpit-ui/.next/` | GENERATED_OR_LOCAL_NOISE | Never commit; safe to ignore after user-approved cleanup. |
| `cockpit-ui/node_modules/` | GENERATED_OR_LOCAL_NOISE | Never commit. |
| `.pytest_cache/`, `.ruff_cache/` | GENERATED_OR_LOCAL_NOISE | Never commit. |
| `financial-engine_v2/reports/runtime_embedding_model.txt`, `financial-engine_v2/reports/news_chunks_embedding_model.txt` | GENERATED_OR_LOCAL_NOISE | Runtime/report metadata; do not integrate as source. |

## Runtime / Data Artifacts That Should Never Be Integrated

These paths exist in fast-dev and are ignored. They must not be committed into canonical:

- `financial-engine_v2/data/fe_local.db`
- `financial-engine_v2/data/ops/ops.db*`
- `financial-engine_v2/data/cockpit/state.db*`
- `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`
- `financial-engine_v2/data/reports/research_memory/market_memory.sqlite`
- `financial-engine_v2/data/reports/research_memory/user_thesis_memory.sqlite`
- `financial-engine_v2/data/reports/research_memory/memory_read_events.jsonl`
- `financial-engine_v2/data/reports/router_metrics_snapshot.json`
- `cockpit-ui/node_modules/`
- `cockpit-ui/.next/`
- caches under `.pytest_cache/` and `.ruff_cache/`

If runtime data needs migration, handle it under a separate Runtime/Ops data-binding task. Do not treat this preservation audit as data-migration approval.

## Must Preserve Before Runtime Rebind

1. The Appendix 5B PRM-inclusive code stack:
   - backend services under `financial-engine_v2/backend/app/services/asx_appendix5b_*.py`
   - focused backend tests under `financial-engine_v2/backend/tests/test_asx_appendix5b_*.py`
   - CLI/gate scripts under `scripts/*appendix5b*.py` and `scripts/run_extraction_evaluation_gates.py`
   - docs updates in `docs/architecture/12_evaluation_and_drift_monitoring.md` and `docs/validation_baseline.md`
2. The ignored Appendix 5B report evidence bundle:
   - `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/`
3. The local Cockpit dev-origin requirement, as an archived runtime note or follow-up design, not as the hard-coded config line.
4. Optional archive-only task cards/reports for automation, sloppy-fix ownership, M40 validation, and older NVMe migration history if the user wants those histories preserved.

## Likely Ignore / Discard Only After User Approval

- `cockpit-ui/next-env.d.ts`
- `cockpit-ui/.next/`
- `cockpit-ui/node_modules/`
- `.pytest_cache/`
- `.ruff_cache/`
- ignored SQLite/data/runtime state under `financial-engine_v2/data/`
- ignored local report outputs not selected for preservation
- hard-coded `allowedDevOrigins` line, after the requirement is captured elsewhere

## Recommended Follow-up Task Cards

| Lane | Task card | Purpose |
| --- | --- | --- |
| Evaluation / Financial Truth | `appendix5b_prm_gate_stack_canonical_integration_v1_20260524` | Integrate the Appendix 5B PRM-inclusive parser/scorer/importer/gate stack and preserve the report evidence bundle. |
| Runtime/Ops / Reporting | `cockpit_dev_origin_rebind_config_v1_20260524` | Replace hard-coded local `allowedDevOrigins` with a safe config/env approach if LAN/Tailscale access is needed after rebind. |
| Repo Hygiene | `fast_dev_archive_only_artifact_preservation_v1_20260524` | Force-preserve selected archive-only task cards/reports, then approve discard of generated/noise files. |
| Runtime/Ops | `fast_dev_data_artifact_rebind_inventory_v1_20260524` | Inventory runtime data paths and decide whether any data migration is needed before service rebind. |

## Smallest Safe Sequence Before Runtime Topology Rebind

1. Keep runtime topology rebind blocked.
2. Open the Appendix 5B integration task against canonical with an explicit allowlist for the service files, tests, scripts, docs, task card, and report evidence bundle.
3. Integrate and validate the Appendix 5B bundle in canonical; include focused backend tests and JSON validation of the PRM report artifacts.
4. Decide the Cockpit `allowedDevOrigins` requirement in a separate Runtime/Ops card; do not commit the local IP line as-is.
5. Decide whether archive-only task cards/reports should be force-preserved.
6. Confirm ignored data/model/cache artifacts are not part of the source integration.
7. Only then rerun the runtime topology audit from canonical and proceed to any approved Docker/systemd/cron/symlink/data-mount rebind.

## Runtime Rebind Verdict

Runtime topology rebind is still blocked.

Reason: fast-dev contains production/evaluation-relevant uncommitted Appendix 5B PRM-inclusive gate work and ignored report evidence absent from canonical.

## Validation Commands / Results

| Command | Result |
| --- | --- |
| `cd /home/l4nd0/tenn && pwd` | `/home/l4nd0/tenn` |
| `readlink -f /home/l4nd0/tenn` | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| `git branch --show-current` | `migration/clean-runtime-baseline-reconstruct-v1` |
| `git rev-parse HEAD` | `e170f6b255ca4229462d4167861775e82ea3df34` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md --write-report` | PASS |
| `python3 scripts/agent_job_registry.py list-active` | PASS, `active_jobs: []` |
| `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md` | FAIL only on unrelated canonical untracked task cards; no active jobs |
| `git -C /home/l4nd0/tenn-fast-dev-storage-v1 rev-list --left-right --count HEAD...$(git -C /home/l4nd0/tenn rev-parse HEAD)` | `0 33` |
| `git -C /home/l4nd0/tenn-fast-dev-storage-v1 diff --stat` | 4 files, 22 insertions, 1 deletion |
| `git -C /home/l4nd0/tenn-fast-dev-storage-v1 ls-files --others --exclude-standard` | 32 files |
| `git diff --check` | PASS, no output |
| `python3 -m json.tool reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/status.json` | PASS |
| `python3 -m json.tool reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/validation.json` | PASS |
| `python3 -m json.tool reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/diff-check.json` | PASS |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md` | FAIL only on the 7 unrelated pre-existing canonical task cards outside this task allowlist |
| Final `python3 scripts/agent_job_registry.py list-active` | PASS, `active_jobs: []` |

## Final Git Status Boundary

Pre-existing canonical untracked task cards were present before this audit:

- `docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md`
- `docs/agent_tasks/cockpit_ui_usefulness_current_head_reapply_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_rerun_v1_20260521.md`
- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`
- `docs/agent_tasks/fresh_session_repo_state_proof_v1_20260524.md`
- `docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md`
- `docs/agent_tasks/runtime_topology_reconciliation_audit_v1_20260522.md`

Final canonical `git status --short --untracked-files=all` shows the 7 pre-existing task cards plus this audit task card. Report artifacts are under ignored `reports/`.

This audit added only:

- `docs/agent_tasks/fast_dev_preservation_audit_v1_20260524.md`
- `reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/README.md`
- `reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/status.json`
- `reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/validation.json`
- `reports/agent_jobs/fast_dev_preservation_audit_v1_20260524/diff-check.json` if generated by validation.

Fast-dev final status was re-read after the report and remained the same 4 tracked modifications plus the same 32 non-ignored untracked files.

## Registry Release Status

No registry claim was acquired, so there was no active claim to release. Final `list-active` returned `active_jobs: []`.

## Project Memory Save Recommendation

Save that `/home/l4nd0/tenn-fast-dev-storage-v1` has no unique commits ahead of canonical, but it contains uncommitted Appendix 5B PRM-inclusive parser/scorer/gate work and ignored report evidence absent from canonical; runtime rebind away from fast-dev remains blocked until that bundle is integrated or explicitly archived/discarded.
