# Extraction Terminal State Candidate Manifest

- Job: `extraction_terminal_state_candidate_manifest_v1_20260527`
- Issue focus: #96
- Lane: Query Orchestration
- Supporting lanes: Evaluation, Financial Truth, Provenance
- Mode: SAFE EXTENSION, report-local/manifest-only

## Session

- Worktree: `/home/l4nd0/tenn-extraction-terminal-state-candidate-manifest-v1-20260527`
- Branch: `safe/extraction-terminal-state-candidate-manifest-v1-20260527`
- Base HEAD: `8f87683c87306267d8280704bf6a0116f4183096`
- Task card: `docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md`
- Registry: shared registry `list-active --read-only` returned no active jobs before claim; overlap check passed; claim succeeded.
- Registry release: succeeded; final `list-active --read-only` returned no active jobs.
- GitHub issue comment: `https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4550583408`
- Collision handling: isolated worktree was created from the committed #99 branch state because the baseline checkout had unrelated untracked task-card dirt.
- Contested surfaces touched: none.
- Collision risk: MEDIUM before isolation due shared evaluation helper file; LOW after isolated worktree and registry checks.

## What Changed

- Added terminal extraction candidate classes and recommendation helpers to `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`.
- Added `build_terminal_extraction_candidate_manifest()` and `terminal_extraction_candidate_manifest_to_csv()`.
- Added focused synthetic tests covering all required classes, missing asset vs existing file/no extraction, correctness-boundary flags, and non-authorizing CSV output.
- Generated report-local JSON/CSV artifacts:
  - `terminal_extraction_candidate_manifest.json`
  - `terminal_extraction_candidate_manifest.csv`

## Manifest Boundary

The generated manifest is a report-local schema and classification artifact. It is not a live production backlog queue and does not authorize broad backfill.

The #96 audit provided aggregate prior counts, not a document-level candidate list. This task card set `production_data_access: false`, so live DB export was not performed. The artifact therefore includes synthetic schema-probe rows for every required class plus prior audit counts in `context`.

## Generated Artifact Summary

```json
{
  "artifact_type": "terminal_extraction_candidate_manifest_v1",
  "manifest_scope": "report_local_schema_proof_prior_audit_context_only",
  "total_document_count": 9,
  "candidate_class_counts": {
    "missing_host_file": 1,
    "file_exists_no_current_terminal_run": 1,
    "stale_extractor_version": 1,
    "completed_with_rows": 1,
    "completed_without_rows": 1,
    "skipped": 1,
    "failed_parser_error": 1,
    "queued_running_orphaned": 1,
    "unknown_needs_audit": 1
  },
  "recommended_action_counts": {
    "blocked_missing_asset": 1,
    "canary_candidate": 1,
    "retry_candidate": 2,
    "review": 3,
    "skip": 2
  },
  "production_data_access": false,
  "broad_backfill_authorized": false
}
```

Prior #96 audit context retained in the artifact:

- 4,011 documents had PDF paths.
- 3,754 documents lacked handled current-version extraction.
- 2,602 of those had host files present.
- 1,152 missing-host-file candidates are inferred from the prior aggregate counts.
- Live stale/failed/skipped/no-run/orphaned split is still `DATA_MISSING`.

## Confirmed

- #96 remains valid: broad runtime coverage/backfill is still blocked by missing document-level terminal-state evidence.
- The manifest contract now defines the required classes: `missing_host_file`, `file_exists_no_current_terminal_run`, `stale_extractor_version`, `completed_with_rows`, `completed_without_rows`, `skipped`, `failed_parser_error`, `queued_running_orphaned`, and `unknown_needs_audit`.
- Recommended actions are constrained to `skip`, `review`, `canary_candidate`, `retry_candidate`, and `blocked_missing_asset`.
- Source asset reviewability is separate from extraction correctness.
- Payload scoreability is separate from terminal extraction state.
- The artifact and helper set `broad_backfill_authorized=false`.
- No broad extraction/backfill, production DB writes, canonical truth writes, Qdrant/news/memory mutation, source PDF changes, parser routing changes, prompt changes, gold-label mutation, runtime/model/GPU config changes, service restarts, Cockpit UI work, or schema changes were performed.

## Inferred

- The prior #96 aggregate `existing_pdf_files_without_handled_current_version_extraction=2602` is the likely first canary candidate pool, but only after a document-level read-only metadata export classifies each row.
- The inferred missing-host-file backlog from the prior aggregate is 1,152 documents (`3754 - 2602`).

## Speculative

- Some stale-version or failed/parser-error rows may be better retry candidates than never-scheduled rows, but this cannot be ranked without live read-only run/error metadata.

## DATA_MISSING

- Document-level live DB candidate list.
- Live split across stale extractor version, failed/parser-error, skipped, queued/running/orphaned, and never-scheduled states.
- Live ok-without-row anomaly list.
- Current queue/scheduler ownership for backlog documents.
- Source asset manifest links for production backlog documents.
- Approved actual extracted payloads for broad #97 scorecard use.

## #96 Advancement

#96 advances from read-only aggregate audit to an executable report-local manifest contract. Future read-only exports can now be classified consistently before any operator-approved canary or bounded backfill.

This does not advance #96 to runtime coverage/backfill execution. The manifest is a decision aid only.

## #97 / #98 / #99 Dependency

- #97 remains the payload correctness layer. Terminal completion does not prove metric correctness; completed rows still need payload scorecard actuals.
- #98 remains the metric-family contract gate. Candidate terminal state does not make unsupported or persisted-only metrics scoreable.
- #99 remains the source reviewability layer. Source asset presence/openability does not count as extraction correctness.

## Remaining Blockers Before Canary/Backfill

- Operator-approved read-only metadata export for document-level terminal states.
- Source asset reviewability links for each candidate row.
- Queue/scheduler ownership check to avoid duplicate work.
- Bounded canary approval with explicit limits.
- #97 actual payloads and thresholds for correctness scoring after canary output exists.
- #98 policy for expanded/persisted-only metric families.
- Explicit operator approval before any retry/canary/backfill execution.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md`: PASS.
- `python3 scripts/agent_job_registry.py list-active --read-only`: PASS, no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`: PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`: PASS.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `uv run --python 3.10 --with pytest --with pydantic-settings==2.6.1 --with pydantic==2.9.2 python -m pytest financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py -q`: PASS, `14 passed, 1 warning in 0.14s`.
- `uv run --python 3.10 --with ruff ruff check financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`: PASS.
- `python3 -m json.tool reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.json`: PASS.
- Raw PDF staging check: PASS, no `.pdf` paths in `git status --short --untracked-files=all`.
- `git diff --check && git diff --cached --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`: PASS, no disallowed files.
- `python3 scripts/agent_job_registry.py release extraction_terminal_state_candidate_manifest_v1_20260527 --repo-root .`: PASS.
- `python3 scripts/agent_job_registry.py list-active --read-only`: PASS, no active jobs after release.
- GitHub issue comment: PASS, `https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4550583408`.
- Code review: no critical or warning findings; residual risk is the intentionally missing live DB candidate list.

## Architecture Review

- `SYSTEM_CONTRACT.md`: compliant. This is report-local triage code and does not alter backend authority, extraction behavior, storage, retrieval, prompts, parser routing, model/runtime config, or canonical truth.
- `.cursor/rules/*`: `DATA_MISSING` in this checkout; the architecture-check skill expected these files, but `.cursor/` was absent.
- GPU process check: not required because this task did not spawn, restart, stop, or depend on `llama-server`.

## Files Changed

- `docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/README.md`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/status.json`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.json`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.csv`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/validation.json`
- `reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/diff-check.json`

## Files Intentionally Not Touched

- Production extraction/backfill paths.
- Production DB, Qdrant, news, memory, and canonical financial truth stores.
- Parser routing and extraction prompts.
- Gold-label fixtures and source PDFs.
- Runtime/model/GPU/service configuration.
- Cockpit UI.
- Persisted database schema and Alembic migrations.

## Final Git Status

At report write time, all changed files are allowlisted and staged for the milestone commit. Final clean status is recorded in the assistant closeout after the commit lands.

## Project Memory Recommendation

Save a memory note after closeout: #96 now has a report-local terminal extraction candidate manifest contract in `extraction_gold_eval_scorecard.py`; the generated artifact is schema/probe-only because production data access was false; broad backfill remains blocked until document-level read-only terminal-state export, source asset links, queue ownership, bounded operator approval, and #97/#98/#99 readiness are complete.
