# Test Matrix

| Required behavior | Test coverage |
|---|---|
| Textual source display includes `claim_verified` sources distinctly | `test_sources_list_preserves_evidence_envelope_roles` |
| Textual source display includes `context_only` sources distinctly | `test_sources_list_preserves_evidence_envelope_roles` |
| `no_hit` does not render as source-backed | `test_sources_list_preserves_evidence_envelope_roles` |
| `degraded_runtime` is visible | `test_sources_list_preserves_evidence_envelope_roles`, `test_sources_show_preserves_envelope_status_and_roles` |
| `local_personal_data` holdings are not financial truth | `test_sources_list_preserves_evidence_envelope_roles` |
| `memory_context` is not claim-verified | `test_sources_list_preserves_evidence_envelope_roles` |
| `financial_truth` remains distinguishable | `test_sources_list_preserves_evidence_envelope_roles` |
| `local_news_context` remains distinguishable | `test_sources_list_preserves_evidence_envelope_roles` |
| Unknown source type falls back safely | `test_sources_list_preserves_evidence_envelope_roles` |
| No-envelope fallback is safe and non-verified | `test_sources_list_without_envelope_falls_back_non_verified` |
| Textual path consumes `QueryOrchestrator.evidence_envelope` | `test_orchestrated_sources_list_consumes_evidence_envelope` |
| Existing legacy list/show behavior remains usable | existing `test_sources_list_and_show` plus fallback assertions |

Regression suites also run existing backend evidence-envelope tests from:

- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_sources.py`
