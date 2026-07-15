# Cockpit API Routing During Metric Extraction

Status: `MERGE_APPROVED`

The code-only lane is complete and locally validated. Keyword-mode Cockpit
chat now constructs the same HybridRouter as structured mode. During registered
metric extraction, non-metric JSON LLM work routes directly to Anthropic while
`multipass_extraction` stays on the deterministic local model. Cockpit's
retired Claude Sonnet 4 model default was migrated to `claude-sonnet-4-6`.

The owner-approved controlled activation recreated only backend, worker, and
GPU worker. Normal and GPU-exclusive stateless proofs returned Anthropic route
metadata, metric extraction remained protected, and DB/news persistence stayed
unchanged. Runtime functionality is `WORKING` for the approved routing scope.

The pre-existing UI outage on port 8081 is separate and was not repaired.
