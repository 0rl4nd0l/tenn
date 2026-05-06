# Test Matrix

## Focused Tests Added

- `test_direct_orchestrator_result_contains_evidence_envelope`
- `test_direct_orchestrator_memory_context_is_not_claim_verified`
- `test_direct_orchestrator_no_hit_financial_truth_is_representable`
- `test_direct_orchestrator_degraded_runtime_is_representable`
- `test_evidence_envelope_distinguishes_source_roles`
- `test_orchestrator_envelope_source_item_is_cockpit_metadata_compatible`
- `test_orchestrator_envelope_preserves_a2m_local_news_as_context`
- `test_unknown_source_type_defaults_to_unclassified_not_verified`

## Requirement Mapping

- Direct result contains envelope: `test_direct_orchestrator_result_contains_evidence_envelope`
- Local news source appears as `local_news_context`: `test_orchestrator_envelope_preserves_a2m_local_news_as_context`
- Financial truth evidence appears as `financial_truth`: `test_direct_orchestrator_result_contains_evidence_envelope`
- Memory context appears as memory/context-only, not claim-verified: `test_direct_orchestrator_memory_context_is_not_claim_verified`
- No-hit representable: `test_direct_orchestrator_no_hit_financial_truth_is_representable`
- Degraded runtime representable: `test_direct_orchestrator_degraded_runtime_is_representable`
- Unknown fallback is non-verified: `test_unknown_source_type_defaults_to_unclassified_not_verified`
- Cockpit-compatible source metadata: `test_orchestrator_envelope_source_item_is_cockpit_metadata_compatible`
- A2M/news regression remains covered/unaffected: `test_orchestrator_envelope_preserves_a2m_local_news_as_context`; no news retrieval code changed
- Holdings/local personal data non-financial-truth: `test_evidence_envelope_distinguishes_source_roles`
