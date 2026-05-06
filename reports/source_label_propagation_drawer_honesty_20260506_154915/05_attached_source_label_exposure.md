# Attached Source Label Exposure

## Fixed Behavior

Attached-source context that is included in the prompt now has corresponding labelled evidence metadata:

- `evidence_label="context_only"`
- `evidence_labels=["context_only"]`
- `claim_verified=false`
- `source_type="attached_source"`

The Cockpit API source builder emits that evidence as a visible `kind="context"` source.

## Guardrails

- Attached sources do not become `financial_truth`.
- Attached sources do not become `claim_verified` solely because the staged chunk has `score=1.0`.
- The patch does not create a transcript index, reindex Qdrant, ingest content, or alter retrieval ranking.
