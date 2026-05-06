# Existing Gap

The prior audit at `reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/` identified G003:

- `ChatController._slash_sources()` owns Textual slash handling.
- The legacy source list path used `SourcesFormatter.format_list()` and `format_show()`.
- The legacy formatter rendered title, source id, score, and doc type.
- It did not render taxonomy fields such as `evidence_label`, `evidence_labels`, `claim_verified`, `no_hit`, `degraded_runtime`, `missing_required_evidence`, `memory_context`, `local_personal_data`, `financial_truth`, `external_web_context`, or `local_news_context`.

Current fix target:

- Keep the shared legacy formatter untouched because `financial-engine_v2/cockpit/core/sources.py` was outside the allowed file list.
- Adapt `chat.py` at the slash-command boundary to prefer the new `QueryOrchestrator.evidence_envelope`.
- Preserve legacy source listing only as a safe fallback with explicit non-verified wording.

Hard-stop checks:

- Source drawer UI changes required: no.
- Legacy `/api/chat` changes required: no.
- Retrieval ranking changes required: no.
- DB/Qdrant/memory mutation required: no.
- Ingestion/reindexing required: no.
- Broad synthesis prompt rewrite required: no.
- Live external services required by tests: no.
