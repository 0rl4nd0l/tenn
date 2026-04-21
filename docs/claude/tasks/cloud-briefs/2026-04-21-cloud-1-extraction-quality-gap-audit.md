# Cloud-1: Extraction-Quality Gap Audit

## Goal

Audit and prioritize the root causes behind remaining `shares_outstanding` misses (notably MIN/TLS) and produce a minimal patch-ready fix plan.

## Scope

- Read:
  - `financial-engine_v2/backend/app/services/extraction.py`
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
  - `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
  - `docs/ops/extraction-truth/phase-02-backlog.md`
- Write:
  - Focused tests and extractor changes only if needed to prove the top-ranked fix.

## Invariants (Do Not Break)

- No inferred values for missing metrics.
- Preserve backend as retrieval/extraction authority.
- No schema migrations.
- No fallback pipelines that bypass canonical extraction flow.

## Validation

```bash
python -m ruff check financial-engine_v2/backend/app/services/extraction.py financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_capability_guards.py
pytest -c pytest.ini financial-engine_v2/backend/tests/test_extraction_gold_eval.py -q
pytest -c pytest.ini financial-engine_v2/backend/tests/test_extraction_capability_guards.py -q
```

## Deliverable

- Ranked findings table: issue, evidence file/line, expected impact, fix complexity.
- If implementing: smallest patch + focused regression tests.
- Final summary of unchanged contract invariants.
