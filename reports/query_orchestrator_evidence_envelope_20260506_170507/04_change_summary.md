# Change Summary

## Files Changed

- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_sources.py`
- `reports/query_orchestrator_evidence_envelope_20260506_170507/**`

## Construction Site

`QueryOrchestrator.orchestrate_query_with_context()` calls `build_evidence_envelope()` after answer input construction and before returning `OrchestratedQueryResult`.

## Return Site

The envelope is returned as `OrchestratedQueryResult.evidence_envelope`.

## Behavior Not Changed

- Cockpit chat path behavior changed: no.
- A2M/news retrieval labels changed: no retrieval code changed; local-news envelope semantics are tested.
- Source drawer UI changed: no.
- Textual `/sources` changed: no.
- Legacy `/api/chat` changed: no.
- Deep research changed: no.
- Retrieval ranking changed: no.
- Financial truth extraction changed: no.
- Qdrant/news/memory/session stores mutated: no.
