# extraction_mainline_core_port_v1_20260607

Status: DONE_WITH_RISK

## Scope

Ported the source-bound multipass extraction core from the migration baseline
onto the mainline stack in a clean sibling worktree:

- Worktree: `/home/l4nd0/tenn-extraction-mainline-core-port-v1-20260607`
- Branch: `safe/extraction-mainline-core-port-v1-20260607`
- Base: `safe/agent-contract-registry-main-v1-20260607` at
  `9d1810cd25d3d9af9e63d012e885760f1df014d0`
- Canonical source reference:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Dirty live checkout was preserved and was not used as the extraction source.

## Files Touched

- `docs/agent_tasks/extraction_mainline_core_port_v1_20260607.md`
- `docs/extraction/metric_extraction_contract.md`
- `financial-engine_v2/backend/app/core/config.py`
- `financial-engine_v2/backend/app/models/asx_financials.py`
- `financial-engine_v2/backend/app/alembic/versions/0004_periodic_financials_period_start_currency.py`
- `financial-engine_v2/backend/app/alembic/versions/0005_add_total_equity_interest_expense.py`
- `financial-engine_v2/backend/app/alembic/versions/0008_asx_structured_created_at.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/services/extraction_run_observability.py`
- `financial-engine_v2/backend/app/services/llamacpp_runtime.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/prompt_registry.py`
- `financial-engine_v2/backend/requirements.txt`
- `financial-engine_v2/backend/tests/test_docling_extract.py`
- `financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py`
- `financial-engine_v2/backend/tests/test_extraction_run_observability.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- `reports/agent_jobs/extraction_mainline_core_port_v1_20260607/README.md`

## Changes

- Restored `run_multipass_extraction()` as a structured `MultipassResult`
  implementation instead of the dirty live checkout's skipped dict stub.
- Restored Docling/PyMuPDF parser routing with data-root cache placement, so
  source PDFs are not used as sidecar cache targets.
- Restored prompt-bundle registry, llama.cpp runtime helper, and extraction-run
  observability helper required by the extraction core.
- Added `settings.data_root` path resolution required by parser cache and
  observability surfaces.
- Restored extraction schema/model compatibility for `period_start`, `currency`,
  `total_equity`, `interest_expense`, and structured-table `created_at`.
- Added `docling>=2.75.0,<3.0.0` as a direct backend requirement.
- Retargeted the restored extraction migrations to mainline's current migration
  chain:
  - `0004` now follows `0002_documents_source_url_unique`.
  - `0008` now follows `0005_add_equity_interest`.
  This avoids pulling unrelated OpenBB, announcement-type, and companies-table
  migrations into the first extraction core port.

## Dependencies

Safe project-venv installs were run only against the existing project venv at
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv`.
No system packages, services, model/GPU config, DBs, Qdrant, Redis, or runtime
state were changed.

Commands:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pip install -r /home/l4nd0/tenn-extraction-mainline-core-port-v1-20260607/financial-engine_v2/requirements-dev.txt
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pip install -r /home/l4nd0/tenn-extraction-mainline-core-port-v1-20260607/financial-engine_v2/backend/requirements.txt
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pip check
```

Outcome:

- Dev requirement install completed and aligned pytest/playwright/respx pins.
- Backend requirement install completed; Docling was already present and
  satisfied by `docling 2.87.0`.
- `pip check`: `No broken requirements found.`

## Validation

All commands below were run from
`/home/l4nd0/tenn-extraction-mainline-core-port-v1-20260607` unless noted.

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_mainline_core_port_v1_20260607.md
```

Result: pass, `ok: true`.

```bash
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Result: pass, `ok: true`, `read_only: true`, `lock_acquired: false`,
`active_jobs: []`.

```bash
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python - <<'PY'
from app.services.docling_extract import DOCLING_VERSION, validate_docling_environment
validate_docling_environment()
print(DOCLING_VERSION)
PY
```

Result: pass, printed `2.87.0`.

```bash
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python - <<'PY'
from app.services.multipass_extraction import run_multipass_extraction, MultipassResult
import inspect
print(inspect.signature(run_multipass_extraction))
print(MultipassResult.__name__)
PY
```

Result: pass, `run_multipass_extraction(...) -> MultipassResult`.

```bash
cd financial-engine_v2/backend
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/tenn /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m alembic -c alembic.ini heads
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/tenn /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m alembic -c alembic.ini history
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/tenn /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m alembic -c alembic.ini upgrade head --sql
```

Result: pass, one head: `0008_asx_structured_created_at`.

SQLite offline SQL generation was also tried and failed before this change's
migrations at existing `0001_init.py` because that baseline migration uses
Postgres `JSONB`. This was recorded as a pre-existing dialect limitation, not a
new regression from this port.

```bash
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile \
  financial-engine_v2/backend/app/core/config.py \
  financial-engine_v2/backend/app/services/llamacpp_runtime.py \
  financial-engine_v2/backend/app/services/prompt_registry.py \
  financial-engine_v2/backend/app/services/extraction_run_observability.py \
  financial-engine_v2/backend/app/services/docling_extract.py \
  financial-engine_v2/backend/app/services/multipass_extraction.py \
  financial-engine_v2/backend/app/models/asx_financials.py \
  financial-engine_v2/backend/app/alembic/versions/0004_periodic_financials_period_start_currency.py \
  financial-engine_v2/backend/app/alembic/versions/0005_add_total_equity_interest_expense.py \
  financial-engine_v2/backend/app/alembic/versions/0008_asx_structured_created_at.py \
  financial-engine_v2/backend/tests/test_docling_extract.py \
  financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py \
  financial-engine_v2/backend/tests/test_extraction_run_observability.py \
  financial-engine_v2/backend/tests/test_multipass_extraction.py \
  financial-engine_v2/scripts/broad_extraction_test.py \
  financial-engine_v2/scripts/test_broad_extraction_test.py
```

Result: pass.

```bash
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_docling_extract.py -q
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_run_observability.py -q
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -q
PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q
PYTHONPATH=financial-engine_v2/backend:financial-engine_v2/scripts /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q
```

Results:

- `test_docling_extract.py`: 17 passed, 1 warning.
- `test_extraction_run_observability.py`: 3 passed, 1 warning.
- `test_extraction_pre_canary_truth_gates.py`: 13 passed, 1 warning.
- `test_multipass_extraction.py`: 184 passed, 1 warning.
- `test_broad_extraction_test.py`: 3 passed.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_mainline_core_port_v1_20260607.md --repo-root . --no-write-report
git diff --check
```

Result: pass, no disallowed files and no whitespace errors.

## Subagent Review

Read-only subagent `019ea1a4-a8d0-7010-8311-05d9ad34f33e` reviewed source refs
and minimal port scope. Its key findings were:

- Use `origin/migration/clean-runtime-baseline-reconstruct-v1` as canonical
  source because the safe post-PR301 branch is byte-identical for the checked
  core files and is merged into migration.
- Keep the first mainline port to deterministic/mocked extraction core, Docling
  parser, observability, prompt registry, llama.cpp helper, and focused tests.
- Do not copy migration requirements wholesale.
- Defer runtime ingestion wiring because current main still routes through
  legacy extraction/pipeline surfaces.

## Unsafe Actions Avoided

- No production DB, Qdrant, Redis, news store, source PDF, gold-label, prompt,
  model/GPU config, service, cron/timer, or runtime-state mutation.
- No broad extraction run, backfill, persistence job, or live DB migration.
- No merge, rebase, cherry-pick, branch deletion, or shared-checkout cleanup.
- No GitHub issue mutation.

## Remaining Risk

- This branch is stacked on PR #317 (`safe/agent-contract-registry-main-v1-20260607`).
  PR #317 must land or this branch must be rebased before mainline merge.
- This port restores the tested core but does not wire live ingestion/runtime
  paths to use it. The next implementation slice should port or reconcile
  extraction runtime routing through `pipeline.py`, `app.services.extraction`,
  and the broader local LLM/router stack.
- Live production extraction remains approval-gated. No claim is made that a
  production backfill, DB migration, live llama.cpp run, or source-PDF canary
  has passed.

## Next Recommended Prompt

Proceed with the next bounded extraction slice: create/validate a task card
stacked after this PR, then port the runtime ingestion wiring so live extraction
paths call the restored `run_multipass_extraction()` contract without touching
production DBs or source PDFs until a separate approved canary.
