# Semantics

No-hit metadata is assigned in:

- `cockpit_api._append_tool_no_hit_source()`
- `cockpit_api._default_source_labels()`
- `cockpit_api._build_ui_sources()`
- `ToolExecutor._annotate_result_semantics()`

Runtime-degraded metadata is assigned in:

- `cockpit_api._append_tool_runtime_failure_source()`
- `cockpit_api._default_source_labels()`
- `cockpit_api._build_ui_sources()`
- `ToolExecutor._annotate_result_semantics()`
- `AgentLoop._merge_evidence_semantic_metadata()`
- explicit web-search handling in `ChatController`

No-hit source verdict:

- No-hit sources are labelled `no_hit`.
- Missing canonical financial rows are labelled `missing_required_evidence` and
  `no_hit`.
- No-hit operational traces are not `claim_verified`.
- No-hit operational traces do not become `financial_truth`.
- A pure operational no-hit/degraded source cannot satisfy the source contract
  for a polished financial claim.

Runtime degraded verdict:

- Web/deep/tool failures are labelled `degraded_runtime` when they affect the
  answer.
- Runtime failure traces remain `operational_trace`.
- Degraded traces do not set `claim_verified`.
- Partial valid evidence remains visible and labelled, while the answer metadata
  also reports `degraded_runtime`.

Regression verdicts:

- A2M/local-news context remains `local_news_context` when source rows carry that
  label.
- Holdings remain local personal data; holdings rows are still kept out of the
  visible source list.
- Memory context remains `memory_context`, not claim-verified or financial truth.
- Attached-source context remains `context_only`; synthetic score does not make
  it claim-verified.
