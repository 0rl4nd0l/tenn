# Cloud-5 Multipass Extraction Performance Profile (2026-04-21)

## Scope
- Profiled deterministic hotspots in `financial-engine_v2/backend/app/services/multipass_extraction.py`.
- Kept extraction outputs and routing contract unchanged.
- Applied only low-risk micro-optimizations.

## Contract Safety Check
- Target layer: Extraction (Pass 1/2 preprocessing utilities and debug capture).
- Preserved invariants: no metric inference, no fallback behavior change, no embedding/vector model changes, no pipeline stage reordering.
- Safety rationale: changes are CPU-only implementation details (regex precompile + equivalent deep copy path for debug capture).

## Hotspot Analysis
Primary hotspot observed in the pre-change benchmark corpus:
- `_detect_currency_from_tables` dominated deterministic CPU time.
- Root cause: repeated `re.findall(...)` calls per currency pattern across combined table text.

## Applied Changes
1. Precompiled `_SCALE_PATTERNS` into `_COMPILED_SCALE_PATTERNS`.
2. Precompiled `_CURRENCY_PATTERNS` into `_COMPILED_CURRENCY_PATTERNS`.
3. Replaced debug capture JSON round-trip with `deepcopy`:
   - from `json.loads(json.dumps(pass3a_results))`
   - to `deepcopy(pass3a_results)`

## Benchmark Method
Environment:
- Python: `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python`
- Import path: `PYTHONPATH=financial-engine_v2/backend`

Workload:
- 20 synthetic tables, 12 rows each, realistic headers/captions/rows.
- Detection benchmark iterations: 5,000.
- Debug capture copy benchmark iterations: 20,000.

Baseline used legacy implementations inline in the benchmark script (same process), then compared against current functions.

## Baseline vs Proposed

| Metric | Baseline (s) | Proposed (s) | Delta (s) | Delta (%) |
|---|---:|---:|---:|---:|
| Scale detection (`_detect_scale_from_tables`) | 0.022302 | 0.018663 | -0.003639 | -16.32% |
| Currency detection (`_detect_currency_from_tables`) | 23.529811 | 19.982404 | -3.547407 | -15.08% |
| Combined detection | 23.552113 | 20.001067 | -3.551047 | -15.08% |
| Debug capture copy path | 1.254779 | 0.252542 | -1.002238 | -79.87% |

## Validation
Commands run:
- `python -m ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/app/services/pipeline.py` ✅
- `pytest -c pytest.ini financial-engine_v2/backend/tests/test_pipeline_observability.py -q` ❌ (file not present on this branch)
- `pytest -c pytest.ini scripts/test_pipeline_observability.py -q` ✅ (7 passed)
- `pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py -k "currency_detection or scale_detection or scale_override" -q` ✅ (7 passed)

## Rollback Plan
If any regression appears:
1. Revert commit on this branch (`git revert <sha>`), restoring previous regex and debug capture logic.
2. Re-run:
   - `python -m ruff check ...`
   - `pytest -c pytest.ini scripts/test_pipeline_observability.py -q`
   - `pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py -k "currency_detection or scale_detection or scale_override" -q`
3. Re-profile the same benchmark workload to confirm rollback behavior.
