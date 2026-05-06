# Next Recommended Prompt

You are Codex working on Tenn.

TASK
Implement the next narrow Source Label Semantics v1 gap after baseline commit `f53b0526a6a`: consistent no-hit and degraded-runtime metadata for non-news tool paths.

PRIMARY LANE
Query Orchestration

SECONDARY LANE
Provenance

EXECUTION MODE
AUDIT MODE first. SAFE EXTENSION MODE only after preflight confirms clean dirty state and no active overlap.

STRICT DO-NOT-TOUCH
Do not edit news/Qdrant runtime files, memory files, extraction logic, parser routing, financial truth, Holdings routing, Marketplace scoring/matching/payload logic, Watchlist route parity, Commentary route parity, chat learning scorer, or broad source-label taxonomy definitions.

SCOPE
Close only these gaps:

- Non-news operational no-hit tools should emit `no_hit` and/or `missing_required_evidence` instead of generic context when a required search/tool path returns no usable evidence.
- Web/deep-research/runtime tool failures should surface `degraded_runtime` only when the answer path actually depends on the failed tool/runtime.

REQUIRED AUDIT

1. Confirm current branch, HEAD, dirty state, active jobs, and changed files.
2. Trace current no-hit and degraded-runtime producers.
3. Identify the narrowest existing metadata/source construction points to extend.
4. Stop if the fix requires chat synthesis redesign, retrieval ranking changes, memory writes, database mutation, Qdrant mutation, or broad taxonomy redesign.

REQUIRED VALIDATION

- Add focused tests proving non-news no-hit labels are not claim verified.
- Add focused tests proving degraded runtime metadata renders as degraded, not source-backed.
- Re-run the f53b052 baseline tests that cover reload preservation and source wording.
- Run `git diff --check`.

FINAL DECISION
Report whether the change completes only the no-hit/runtime gap or whether Source Label Semantics v1 still has remaining taxonomy coverage work.
