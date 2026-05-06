# Tests And Validation

Passed:

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestChatWithTennTickerPropagation -q
```

Result: `6 passed in 1.94s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop.py -k "ticker_company_overview or ticker_news_prefetch or no_resolved_ticker" -q
```

Result: `3 passed, 34 deselected in 1.13s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q
```

Result: `54 passed in 1.15s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop.py -q
```

Result: `37 passed in 0.17s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -k "holdings" -q
```

Result: `3 passed, 43 deselected in 2.12s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/cockpit/tests/test_agent_loop.py -q
```

Result: `83 passed in 4.27s`

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests -k "a2m or news or retrieval or holdings" -q
```

Result: `142 passed, 1066 deselected, 8 warnings in 29.25s`

```text
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/cockpit/core/agent_loop.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py financial-engine_v2/cockpit/tests/test_agent_loop.py
```

Result: `All checks passed!`

```text
git diff --check
```

Result: passed with no output.

Broad backend selector:

```text
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "a2m or news or rag or retrieval" -q
```

Result: `146 passed, 3 failed, 1298 deselected, 6 warnings in 26.17s`

Failures were in unrelated pipeline/vector guardrail tests:

- `financial-engine_v2/backend/tests/test_rag_payload_guardrails.py::test_process_document_deletes_existing_points_before_upsert`
- `financial-engine_v2/backend/tests/test_rag_payload_guardrails.py::test_process_document_skips_invalid_chunk_payloads`
- `financial-engine_v2/backend/tests/test_rag_payload_guardrails.py::test_process_document_upserts_financial_rows_for_ok_low_confidence`

These failures do not touch the changed files or the chat/news selection path. They were recorded and not fixed because pipeline ingestion/vector guardrails are outside this task boundary.
