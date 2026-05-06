# Change Summary

## `financial-engine_v2/cockpit/core/chat.py`

Added small Textual-only helpers that:

- detect evidence envelopes by their existing contract fields,
- collect envelopes from evidence entries under `details.evidence_envelope` or `result.evidence_envelope`,
- flatten envelope `sources`,
- render `/sources list` with taxonomy version, coverage status, source status, exact evidence labels, item counts, claim-verification flag, no-hit flag, degraded flag, missing-evidence flag, and errors,
- render `/sources show <n>` with the same role/status fields in a detailed view,
- fall back safely when no envelope exists.

`_build_orchestrated_response()` now copies `orchestration_result.evidence_envelope` into the orchestrator evidence payload when available.

`_set_latest_sources_payloads()` now stores envelope payloads ahead of legacy source payloads so `/sources list` and `/sources show <n>` consume the envelope first.

## Tests

`financial-engine_v2/cockpit/tests/test_slash_commands.py` now proves:

- `claim_verified` is rendered distinctly.
- `context_only` is rendered distinctly.
- `no_hit` is visible and not source-backed.
- `degraded_runtime` is visible.
- `local_personal_data` holdings are not rendered as financial truth.
- `memory_context` is not claim-verified.
- `financial_truth` remains distinguishable.
- `local_news_context` remains distinguishable.
- `unknown_unclassified` is not claim-verified.
- no-envelope fallback is safe and non-verified.

`financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py` now proves the orchestrated chat path stores `QueryOrchestrator.evidence_envelope` for Textual `/sources list`.

## Not Changed

- No ingestion code.
- No Qdrant code.
- No `news.sqlite` code.
- No memory DB code.
- No retrieval ranking code.
- No financial truth extraction code.
- No source drawer UI code.
- No legacy `/api/chat` code.
- No marketplace, watchlist, commentary, or unrelated dirty files.
