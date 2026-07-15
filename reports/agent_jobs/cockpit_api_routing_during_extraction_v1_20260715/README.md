# Cockpit API Routing During Metric Extraction

Status: `DONE_WITH_RISK`

The code-only lane is complete and locally validated. Keyword-mode Cockpit
chat now constructs the same HybridRouter as structured mode. During registered
metric extraction, non-metric JSON LLM work routes directly to Anthropic while
`multipass_extraction` stays on the deterministic local model. Cockpit's
retired Claude Sonnet 4 model default was migrated to `claude-sonnet-4-6`.

The live Cockpit service was not restarted or modified. Live runtime behavior
therefore remains `DATA_MISSING` until a separately approved activation lane.
