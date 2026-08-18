
# Validation

Generated: 2026-06-23T07:54:28.496693Z

Commands run:

```bash
UV_CACHE_DIR=/tmp/tenn-uv-cache-extraction-measure-20260623 uv run --with pytest --with python-dateutil --with pydantic --with pydantic-settings --with sqlalchemy --with numpy --with pandas --with qdrant-client --with httpx --with PyMuPDF pytest -q financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_rebinds_annual_report_title_date_to_source_period_end
```

Result: 1 passed.

```bash
UV_CACHE_DIR=/tmp/tenn-uv-cache-extraction-measure-20260623 uv run --with pytest --with python-dateutil --with pydantic --with pydantic-settings --with sqlalchemy --with numpy --with pandas --with qdrant-client --with httpx --with PyMuPDF pytest -q financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_uses_explicit_front_matter_period_end_when_pass1_misses_it financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_blocks_title_only_half_year_period_end_distinct_when_pass1_misses_it financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_uses_source_text_half_year_period_end_distinct_when_pass1_misses_it financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_opt_in_routes_openability_tables_through_existing_gates financial-engine_v2/backend/tests/test_multipass_extraction.py::test_validate_gate_rejects_half_year_announcement_date_period_end financial-engine_v2/backend/tests/test_multipass_extraction.py::test_validate_gate_allows_half_year_period_end_distinct_from_announcement_date
```

Result: 7 passed.

```bash
UV_CACHE_DIR=/tmp/tenn-uv-cache-extraction-measure-20260623 uv run --with httpx --with PyMuPDF --with pydantic --with pydantic-settings --with sqlalchemy --with numpy --with pandas --with qdrant-client python scripts/extraction_no_write_replay.py --case-manifest financial-engine_v2/data/extraction_no_write_cases/guard_cases_v1.json --case WHC --report-dir reports/agent_jobs/extraction_measure_then_fix_top_failure_class_v1_20260623/affected_replay --profile baseline-no-write --case-timeout-seconds 300
```

Result: PASS, `side_effect_pass=true`, expectation failures 0, WHC period_end `2022-06-30`.

Warnings:
- Pytest emitted the existing `asyncio_default_fixture_loop_scope` unknown config warning under ephemeral uv pytest.
- The first version of the new regression failed with `validation_gate:insufficient_metrics:1`; the mock was corrected to include enough unrelated metrics. This was not a product failure.
