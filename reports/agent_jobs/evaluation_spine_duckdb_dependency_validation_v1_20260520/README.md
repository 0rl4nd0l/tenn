# Evaluation Spine DuckDB Dependency Validation v1

## Confirmed Facts

- Worktree: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Starting HEAD: `d00110b30232` (`feat(evaluation): add offline eval spine manifest foundation`).
- Starting `git status --short`: clean.
- Task card validation: passed.
- Registry preflight: `active_jobs=[]`; overlap check passed; job was claimed.
- Local system Python did not have `duckdb` installed.
- `uv run --with duckdb --with pytest` made DuckDB available without changing production/runtime dependency files.
- DuckDB Python package version used for validation: `1.5.2`.

## Inferred Facts

- Root `requirements.txt` is a production/runtime-oriented install chain because it includes `financial-engine_v2/backend/requirements.txt` and `financial-engine_v2/worker/requirements.txt`, and CI installs root `requirements.txt`.
- `financial-engine_v2/backend/requirements-dev.txt` is dev-only and already contains `duckdb>=1.4.0,<2.0`, but it is backend-scoped rather than reporting-scoped.
- A reporting-only dependency file is the narrowest durable mechanism for this task.

## DATA_MISSING

- Final commit hash is self-referential and cannot be embedded into the committed report before the commit exists; it is reported in the final closeout.
- Registry release status is pending at report-write time; it is reported in the final closeout after the commit.
- No scorecard rows existed in the three source manifests used for the smoke, so scorecard-profile guard persistence was not exercised by this real-data smoke.

## Dependency Mechanism Chosen

Added `scripts/reporting/requirements.txt`:

```text
duckdb>=1.4.0,<2.0
```

This keeps DuckDB scoped to offline reporting/dev tooling. No backend runtime,
worker runtime, Docker, service, env, Qdrant, news, memory, extraction/parser,
Cockpit/Home, model/GPU, or financial truth path dependency was changed.

## Files Changed

- `docs/agent_tasks/evaluation_spine_duckdb_dependency_validation_v1_20260520.md`
- `docs/evaluation_spine_manifest_contract.md`
- `scripts/reporting/requirements.txt`
- `reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/README.md`
- `reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/duckdb_smoke_summary.json`
- `reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/status.json`
- `reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/validation.json`
- `reports/agent_jobs/evaluation_spine_duckdb_dependency_validation_v1_20260520/diff-check.json`

## Exact Install and Validation Commands

```bash
uv run --with duckdb --with pytest python - <<'PY'
import duckdb
print(duckdb.__version__)
PY

python3 scripts/reporting/eval_spine_manifest.py --help
python3 scripts/reporting/eval_spine_ingest.py --help
uv run --with duckdb --with pytest python -m pytest scripts/reporting/test_eval_spine_manifest.py scripts/reporting/test_eval_spine_ingest.py -q
```

Temporary manifest build and validation:

```bash
python3 scripts/reporting/eval_spine_manifest.py build --task-card docs/agent_tasks/evaluation_spine_manifest_foundation_v1_20260520.md --report-dir reports/agent_jobs/evaluation_spine_manifest_foundation_v1_20260520 --out /tmp/tenn_eval_spine_smoke_manifests/evaluation_spine_manifest_foundation_v1_20260520.json
python3 scripts/reporting/eval_spine_manifest.py validate /tmp/tenn_eval_spine_smoke_manifests/evaluation_spine_manifest_foundation_v1_20260520.json
python3 scripts/reporting/eval_spine_manifest.py build --task-card docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md --report-dir reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520 --out /tmp/tenn_eval_spine_smoke_manifests/news_retrieval_parity_a2m_integration_v1_20260520.json
python3 scripts/reporting/eval_spine_manifest.py validate /tmp/tenn_eval_spine_smoke_manifests/news_retrieval_parity_a2m_integration_v1_20260520.json
python3 scripts/reporting/eval_spine_manifest.py build --task-card docs/agent_tasks/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520.md --report-dir reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520 --out /tmp/tenn_eval_spine_smoke_manifests/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520.json
python3 scripts/reporting/eval_spine_manifest.py validate /tmp/tenn_eval_spine_smoke_manifests/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520.json
```

Real DuckDB ingest smoke:

```bash
uv run --with duckdb python3 scripts/reporting/eval_spine_ingest.py --db /tmp/tenn_eval_spine_smoke.duckdb /tmp/tenn_eval_spine_smoke_manifests/evaluation_spine_manifest_foundation_v1_20260520.json /tmp/tenn_eval_spine_smoke_manifests/news_retrieval_parity_a2m_integration_v1_20260520.json /tmp/tenn_eval_spine_smoke_manifests/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520.json
```

## Offline Ingest Smoke Results

- DB path: `/tmp/tenn_eval_spine_smoke.duckdb`.
- DB file committed: no.
- Inserted run IDs:
  - `evaluation_spine_manifest_foundation_v1_20260520`
  - `news_retrieval_parity_a2m_integration_v1_20260520`
  - `asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520`

Table row counts from read-only DuckDB query:

| Table | Rows |
| --- | ---: |
| `artifact_runs` | 3 |
| `task_cards` | 3 |
| `validation_commands` | 24 |
| `artifact_files` | 12 |
| `data_missing_items` | 14 |
| `decisions_and_verdicts` | 2 |
| `scorecard_results` | 0 |
| `dirty_worktree_events` | 0 |
| `registry_events` | 0 |

Coverage checks:

- `artifact_runs` had the expected three rows.
- `task_cards` had rows for all three manifests.
- `validation_commands` had rows where available: 24 rows for `evaluation_spine_manifest_foundation_v1_20260520`.
- `data_missing_items` preserved DATA_MISSING rows for all three manifests.
- `decisions_and_verdicts` preserved verdict rows where available: two rows for `asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520`.
- Scorecard profile guard: not applicable for this smoke because no source manifest contained scorecard rows.

## Test Results

- `python3 scripts/reporting/eval_spine_manifest.py --help`: passed.
- `python3 scripts/reporting/eval_spine_ingest.py --help`: passed.
- `uv run --with duckdb --with pytest python -m pytest scripts/reporting/test_eval_spine_manifest.py scripts/reporting/test_eval_spine_ingest.py -q`: `10 passed, 1 warning`.

## Safety Boundary Confirmation

- Production data access: false.
- Backend runtime dependency files changed: no.
- Docker/systemd/service/env files changed: no.
- Qdrant/news/memory/extraction/parser/Cockpit/Home/source-label/model/GPU/financial truth paths changed: no.
- DuckDB DB files committed: no.

## Final Status

- Final `git diff --check`: passed.
- Task-card `check-diff`: passed.
- Final staged DB-file check: passed; no `.duckdb`, `.db`, `.sqlite`, or `.sqlite3` files staged.
- Final backend/runtime staged-file check: passed; no backend runtime, Docker, service, env, extraction/news, Cockpit, Home, Qdrant, memory, model/GPU, or financial truth files staged.
- Final git status before commit: staged allowed files only.
- Registry release status: released; final `list-active` returned `active_jobs=[]`.
- Commit hash if committed: DATA_MISSING until final commit exists.

## Project Memory Save Recommendation

`SAVE_RECOMMENDED`: save the narrow dependency pattern that keeps DuckDB in
`scripts/reporting/requirements.txt` and validates ingest via `uv run --with
duckdb` without changing production/runtime dependency paths.
