# LBL Income Row Ref Repair

Status: `DONE_WITH_RISK`

## Objective

Implemented one bounded repair for LBL-style presentation income table row-ref
provenance so `revenue`, `ebit`, and `np_attributable` keep source-bound row
labels instead of `unknown`.

## Current State

- Worktree: `/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616`
- Branch: `safe/extraction-lbl-income-row-ref-repair-v1-20260616`
- Base/upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD: `85250db58bc4ebd5b3e46790311afc7ec7e5b910`
- Task card: `docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`
- Registry read-only state: no active jobs.
- Task ledger: `DATA_MISSING` for both live registry ledger and committed
  ledger files.
- Duplicate-work classification: `SUPERSEDED_IGNORE` for older merged LBL
  companion-period work, `PRESERVE` for stale dirty post-PR346 report-only
  branch, and `pass` for this fresh origin-based bounded implementation lane.

## Evidence Used

- `/home/l4nd0/tenn-lbl-bounded-runtime-execution-v1-20260616/reports/agent_jobs/extraction_lbl_bounded_runtime_execution_v1_20260616/README.md`
- `failure_classification.json`: strict acceptance failed on unknown row refs.
- `metric_table.json`: `revenue`, `ebit`, and `np_attributable` row refs were
  `unknown`.
- `provenance_summary.json`: page 21 income table contains `Sales Revenue`,
  `EBIT`, and `NPAT For` row labels for those metrics.

## Implementation

- Added deterministic expansion for income-statement row refs when the LLM
  returns the observed combined `metric_name` row-ref value.
- The expansion only uses labels present in the same table markdown and only
  fills missing or `unknown` refs for `revenue`, `ebit`, and
  `np_attributable`.
- Existing values, period, scale, currency, source table, page, and validation
  behavior are preserved.

## Runtime Replay Result

- Runtime status: `ok`
- Runtime error: `None`
- Period: `H` ending `2025-12-31`
- Scale/currency: `thousands` / `AUD`
- Non-null metrics: `7`
- Target row refs:
  - `revenue`: `Sales Revenue`
  - `ebit`: `EBIT`
  - `np_attributable`: `NPAT For`

## Files Touched

- `docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/README.md`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/status.json`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/live_git_status.json`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/evidence_summary.json`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/red_test.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/green_test.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/py_compile.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/ruff.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_stdout.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_stderr.log`
- `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/diff-check.json`

## Files Intentionally Not Touched

- Source PDFs.
- DB, Qdrant, Redis, news stores, memory, prompts, gold labels, schemas,
  runtime config, model config, and GPU config.
- GitHub issues and PRs.
- Count-24/count-32/random-sample/broad extraction surfaces.

## Commands Run

- `git fetch origin migration/clean-runtime-baseline-reconstruct-v1`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`:
  exit 0, no active jobs.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md`:
  exit 0.
- RED test with `pytest` on PATH: exit 127, `pytest` unavailable.
- RED test with `uv run --with-requirements ... pytest -q ...::test_pass3a_expands_lbl_income_combined_metric_name_row_refs`:
  exit 1, expected missing per-metric row refs.
- GREEN test with the same `uv run` command: exit 0.
- `uv run ... python -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`:
  exit 0.
- Single-document LBL bounded replay: exit 0, runtime status `ok`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`:
  exit 0.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_lbl_income_row_ref_repair_v1_20260616.md --repo-root .`:
  exit 0.

## Raw Logs

- `red_test.log`
- `green_test.log`
- `py_compile.log`
- `ruff.log`
- `lbl_replay_stdout.log`
- `lbl_replay_stderr.log`
- `lbl_replay_summary.json`

## Unsafe Actions Avoided

No count-24/count-32, random samples, broad extraction, backfills, full ticker
extraction, canonical writes, GitHub writes, or mutation of DB/Qdrant/Redis/news
/memory/source PDFs/prompts/gold/schema/runtime/model/GPU config.

## Blocked Items And DATA_MISSING

- Live task ledger file was missing at the registry root.
- Committed task ledger `docs/agent_registry/task_ledger/LEDGER.jsonl` was
  missing.

## Remaining Risk

- Replay stderr includes existing pydantic protected-namespace warnings and one
  cashflow pass3a timeout followed by the built-in truncated-table retry; final
  runtime status was `ok`.
- Report artifacts are under ignored `reports/`, so they need `git add -f` only
  if this work is later committed.

## Next Recommended Prompt

Review and commit the bounded LBL row-ref repair from
`/home/l4nd0/tenn-lbl-income-row-ref-repair-v1-20260616` if the local diff is
acceptable. Do not run broader extraction until that commit is reviewed.
