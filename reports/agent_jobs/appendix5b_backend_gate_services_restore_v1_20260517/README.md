# Appendix 5B Backend Gate Services Restore

## 1. Executive summary

Restored the existing Appendix 5B backend parser/candidate/scorer service stack and recurring gate scripts into active NVMe. Generated a controlled Docling PRM candidate artifact in this task output, verified it against the prior approval packet, and promoted PRM Dec 2025 into the report-local Appendix 5B no-regression floor only after the PRM-inclusive recurring gate passed.

## 2. Confirmed facts

- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- HEAD at task start: `55f746aabb10`
- Source commits locally visible: `ae2dfd81cdfc`, `5d08ee34cb2e`, `55f746aabb10`
- Task-card validation passed with repo tooling.
- Registry `list-active` returned no active jobs.
- Registry claim failed because unrelated pre-existing dirty task cards were outside this task card's allowed files.
- Graphify report/wiki are absent in active NVMe.

## 3. Inferred facts

- The source no-regression wrapper needed `app.services.asx_appendix5b_candidate_scorer`, which in turn depends on the restored Appendix 5B service family.
- PRM is safe to include in the report-local floor because the Docling candidate and approval-packet evidence bind to the same page, line, column, raw value, scale, and normalized expected value.

## 4. DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` are not present in active NVMe.
- Active NVMe has no local `financial-engine_v2/.venv`; validation used `/mnt/hdd-data/home/l4nd0/tenn/.venv` only as a tooling interpreter against active NVMe files.
- No registry claim was acquired because unrelated dirty task-card files blocked the generic claim precheck.

## 5. Preflight results

- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git branch --show-current`: `fast/dev-storage-v1-20260513-170304`
- `git rev-parse --short=12 HEAD`: `55f746aabb10`
- Initial dirty state: untracked `docs/agent_tasks/appendix5b_gate_stack_prm_promotion_v1_20260517.md` and `docs/agent_tasks/m40_8001_conservative_validation_v1_20260517.md`.
- `git log --oneline -12`: top commit `55f746aa milestone(evaluation): packet appendix 5b fifth doc evidence`.
- Source worktree `/home/l4nd0/tenn-appendix5b-10x-no-regression-suite-v1-20260517`: clean.
- Source worktree `/home/l4nd0/tenn-appendix5b-recurring-gate-integration-v1-20260517`: dirty only in `reports/agent_jobs/appendix5b_recurring_gate_integration_v1_20260517/status.json`.
- PRM approval packet exists and reports `(246)` / `-246000 AUD`.
- Prior blocked report exists and identifies the missing Appendix 5B backend service files.

## 6. Source commits/worktrees inspected

- `ae2dfd81cdfc`: repeatable 10X no-regression gate branch/worktree.
- `5d08ee34cb2e`: recurring gate integration branch/worktree; used as restore source.
- `55f746aabb10`: PRM approval packet on active NVMe.

## 7. Missing backend service inventory

Restored service files:

- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_artifacts.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_candidate_scorer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_confirmed_label_importer.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_label_review_packet.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_manifest_builder.py`
- `financial-engine_v2/backend/app/services/asx_appendix5b_parser.py`

## 8. Files restored into active NVMe

Restored the service files above plus focused Appendix 5B backend tests and the Appendix 5B gate/helper scripts listed in `service_inventory.json`.

## 9. PRM approval packet verification

- Approval packet found: yes.
- Evidence matched: PDF page 8, Appendix 5B page 1, line `1.9`, `Current quarter $A'000`, raw `(246)`, normalized `-246000 AUD`.
- Generated candidate: raw `(246)`, parser value `-246.0`, scale `thousands`, normalized scorer value `-246000`.

## 10. Whether PRM was added to the no-regression floor

Yes. PRM Dec 2025 was added to the report-local no-regression floor after the PRM-inclusive gate passed.

## 11. Gate results before/after

- Source 10X gate summary: pass, 6 scored docs, 4 labelled document passes, 12 labelled metrics, exact-match `1.0`, coverage `1.0`.
- PRM-inclusive gate summary: pass, 7 scored docs, 5 labelled document passes, 13 labelled metrics, exact-match `1.0`, coverage `1.0`.

## 12. Backend import/test results

- Backend import check: PASS (`import_check.txt`).
- Focused backend pytest: `40 passed in 0.26s`.

## 13. Other tests/checks run with exact results

- Recurring wrapper: PASS, `gate_count=1`, no failed gates.
- Focused gate pytest: `7 passed in 0.12s`.
- Targeted ruff: PASS, `All checks passed!`.
- JSON artifact checks: PASS, `JSON_OK`.
- Heavy-file guard in task output: PASS, no raw PDF/tmp/core/generated file over threshold reported.
- `git diff --check`: PASS, no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/appendix5b_backend_gate_services_restore_v1_20260517.md`: FAIL only for unrelated outside-scope dirty files: `cockpit-ui/next-env.d.ts`, `docs/agent_tasks/appendix5b_gate_stack_prm_promotion_v1_20260517.md`, and `docs/agent_tasks/m40_8001_conservative_validation_v1_20260517.md`.

## 14. Files changed

See `status.json` for the full changed-file list.

## 15. Files intentionally not touched

- Dirty preserve checkout content.
- Extraction prompts.
- Canonical financial truth write paths.
- Production DB, Qdrant, news, and memory state.
- Rented GPU/runtime/UI/Home/news surfaces.
- Appendix 4C/4D/4E scope.

## 16. Risks and blockers

- Registry claim was blocked by unrelated dirty task-card files outside this task card's allowed files.
- A separate unrelated `cockpit-ui/next-env.d.ts` modification appeared in active NVMe during the session and was not touched by this task.
- Check-diff reports only unrelated outside-scope dirty files after exact restored paths were added to the card.

## 17. Recommended next safe step

Commit the restored Appendix 5B gate/service stack and PRM-inclusive report-local floor. Then save memory for the new recurring floor state.

## 18. Project Memory save recommendation

Save that active NVMe restored the Appendix 5B backend scorer/parser/candidate services and promoted PRM Dec 2025 into the report-local no-regression floor after the recurring gate passed with 5 labelled documents and 13/13 labelled metrics.

## 19. Final repo/worktree status

Final status includes this task's restored files plus unrelated pre-existing task cards and an unrelated `cockpit-ui/next-env.d.ts` modification. Reports under `reports/agent_jobs/...` are ignored by git status in this checkout.

## 20. Registry claim/release status if supported

- `list-active`: PASS, no active jobs.
- `claim`: FAIL, blocked by unrelated dirty task-card files outside this task card's allowed files.
- Final `list-active`: one unrelated active `m40_8001_conservative_validation_v1_20260517` job appeared after this work; no overlap with Appendix 5B/backend eval restored surfaces.
- `release`: not run because no claim was acquired.
