# Decisions

## D1: Disable Attach For Evidence-Only By Default

Decision: For `decision_limit=evidence_only`, local readonly config
verification is not sufficient when `OPENCODE_SERVER_URL` would route execution
through `opencode run --attach`. The bridge should fail closed unless remote
readonly enforcement is explicitly proven.

Current implementation target: disable attach mode for evidence-only workers
because no remote proof mechanism exists in the bridge yet.

## D2: Requested Decision Limit Is Authoritative

Decision: Result validation must compare worker output to the requested
`decision_limit` from args or metadata. Worker-supplied `decision_limit` must
not be able to relax evidence-only checks.
