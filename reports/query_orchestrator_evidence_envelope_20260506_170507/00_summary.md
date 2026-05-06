# Summary

## Final Verdict

G005 is fixed for direct `QueryOrchestrator` results.

`OrchestratedQueryResult` now includes an additive `evidence_envelope` field built in `financial-engine_v2/backend/app/services/query_orchestrator.py`. The envelope uses `source_label_semantics_v1` labels and exposes conservative, backend-neutral source/evidence metadata without changing retrieval order, provider selection, financial truth extraction, memory writes, Qdrant, `news.sqlite`, Textual `/sources`, legacy `/api/chat`, or the source drawer UI.

## Direct Envelope Verdicts

- Direct result contains an envelope: yes.
- No-hit representable: yes, via `no_hit`; missing financial truth for numeric plans also uses `missing_required_evidence`.
- Degraded runtime representable: yes, via `degraded_runtime` plus `operational_trace`.
- Financial truth distinguishable: yes, positive financial rows/snapshots are `financial_truth`.
- Local news distinguishable: yes, source names/types with news semantics are `local_news_context`.
- Memory distinguishable: yes, company/market/thesis memory is `memory_context` and `context_only`, not `claim_verified`.
- Web distinguishable: yes, web source names/types are `external_web_context`.
- Holdings/local personal data distinguishable: yes, holdings/portfolio/watchlist-like sources are `local_personal_data`, not `financial_truth`.
- Unknown source fallback: yes, `unknown_unclassified` and non-verified.

## Cockpit/A2M Regression

Existing Cockpit chat wrapping was not changed. A focused compatibility test verifies envelope source items carry the same `evidence_labels` key shape accepted by the existing Cockpit source normalizer. A2M ticker-news semantics remain covered by a local-news envelope test and no retrieval/news ranking code was changed.
