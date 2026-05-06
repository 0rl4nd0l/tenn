# Envelope Contract

## Result Field

`OrchestratedQueryResult.evidence_envelope`

## Envelope Fields

- `source_label_taxonomy_version`
- `sources`
- `evidence_labels`
- `source_label_counts`
- `source_coverage_status`
- `claim_verified_source_count`
- `missing_categories`
- `sufficient_for_analysis`

## Per-Source Fields

- `source_name`
- `source_id`
- `status`
- `source_role_labels`
- `evidence_label`
- `evidence_labels`
- `item_count`
- `has_evidence`
- `claim_verified`
- `no_hit`
- `degraded`
- `missing_required_evidence`
- `missing_categories`
- `error`

## Taxonomy Labels

The envelope accepts and emits:

- `claim_verified`
- `context_only`
- `no_hit`
- `operational_trace`
- `local_personal_data`
- `memory_context`
- `external_web_context`
- `local_news_context`
- `financial_truth`
- `degraded_runtime`
- `missing_required_evidence`
- `unknown_unclassified`

## Conservative Rules

- The orchestrator envelope does not set `claim_verified`; direct claim support is not proven at this layer.
- Positive financial rows or snapshots are `financial_truth`.
- Planned financial truth with no rows/snapshot for numeric needs is `missing_required_evidence`, `no_hit`, and not `financial_truth`.
- Memory evidence is `memory_context` plus `context_only`.
- Local news evidence is `local_news_context` plus `context_only`.
- Web evidence is `external_web_context` plus `context_only`.
- Holdings/local personal data is `local_personal_data` plus `context_only`.
- Unknown evidence is `unknown_unclassified` plus `context_only`.
- Empty/no-result paths are `no_hit`; degraded/error paths are `degraded_runtime` plus `operational_trace`.
