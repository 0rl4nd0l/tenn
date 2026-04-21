# Cloud-3: Extraction-Truth Real-Gold Eval Pass

## Goal

Run the current real-gold evaluation flow and produce a reproducible failure taxonomy with highest-impact fix targets.

## Scope

- Read:
  - `scripts/run_real_extraction_eval.py`
  - `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - `docs/ops/extraction-truth/phase-02-backlog.md`
  - `docs/ops/extraction-truth/phase-05-canonical-eval-policy.md` (if present)
- Write:
  - Report artifact only (no mandatory runtime code changes in this task).

## Invariants (Do Not Break)

- No evaluator rule changes without explicit evidence and tests.
- No data rewriting in Qdrant/Postgres.
- No synthetic score inflation.

## Validation

```bash
bash scripts/setup_eval_cloud.sh
python -m pytest -c pytest.ini scripts/test_run_real_extraction_eval.py -q
python scripts/run_real_extraction_eval.py --help
```

## Deliverable

- Reproducible run metadata (command, commit SHA, date, env assumptions).
- Failure taxonomy by ticker, metric, and failure mode.
- Top 10 fix candidates ordered by expected accuracy gain and implementation risk.
