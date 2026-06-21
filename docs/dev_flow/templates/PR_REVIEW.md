# PR Review

Use this template for the Tenn final diff/PR review gate. It replaces the
visible `tenn-code-reviewer` skill entrypoint while preserving the same
read-only review stance.

Decision: <pass|pass_with_risk|revise|block>

## Scope
- Branch/HEAD:
- Base:
- Task card:
- Diff files:

## Findings
- Severity: <critical|high|medium|low>
  - File:
  - Issue:
  - Evidence:
  - Recommendation:

## Validation Evidence
- `<command>`: <exit/status>

## Runtime Functionality Proof
- Required for this diff: <yes|no>
- intended output:
- live output location:
- pre-run max timestamp or count:
- post-run max timestamp or count:
- rows/files inserted or updated after run start:
- readiness/gate status:
- exact command/query used:
- result: <WORKING|PARTIAL|BROKEN|DATA_MISSING|not_applicable>
- remaining blocker:

## Docs Impact
- docs_impact: <DOCS_NOT_REQUIRED|DOCS_UPDATED|DOCS_FOLLOWUP|DATA_MISSING>
- docs_checked:
  - <path or none>
- docs_changed:
  - <path or none>
- docs_followup:
  - <issue, task card, report path, or none>
- reason: <short reason>

## Model And Subagent Routing
- task_tier: <small|medium|large|critical>
- recommended_model: <mini/low-cost|standard coding model|high reasoning|high reasoning plus review-board>
- actual_model: <model tier used or DATA_MISSING>
- why_this_model: <short reason>
- worker_model_allowed: <mini/low-cost|standard coding model|high reasoning|not_applicable>
- worker_decision_limit: <evidence_only|recommendation_only|bounded_implementation|not_applicable>
- escalation_needed: <yes|no>

## Diff Discipline
- Smallest safe readable diff: <yes|no>
- Unnecessary abstraction added: <yes|no>
- Unfilled templates imply approval/success: <yes|no>
- Counter-lineage required for metrics/evaluation reporting: <yes|no>

## Boundary Check
- Product/runtime/data/extraction paths changed: <yes|no>
- Host-global files changed: <yes|no>
- GitHub mutation approved: <yes|no|not_applicable>
