# Cloud-5: Multipass Extraction Performance Profile

## Goal

Profile multipass extraction latency and identify low-risk performance improvements with measurable impact.

## Scope

- Read:
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/app/services/pipeline.py`
  - `financial-engine_v2/backend/tests/test_pipeline_observability.py`
  - `reports/` latest extraction/eval timing artifacts
- Write:
  - Report artifact and optional micro-optimizations with tests.

## Invariants (Do Not Break)

- No extraction correctness regressions.
- No contract-violating fallback behavior.
- No embedding/vector model changes.

## Validation

```bash
python -m ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/app/services/pipeline.py
pytest -c pytest.ini financial-engine_v2/backend/tests/test_pipeline_observability.py -q
```

## Deliverable

- Benchmark table: baseline vs proposed deltas.
- Hotspot analysis: top latency contributors.
- Low-risk optimization list with expected gain and rollback plan.
