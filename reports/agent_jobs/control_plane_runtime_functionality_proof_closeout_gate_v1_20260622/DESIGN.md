# Runtime Functionality Proof Closeout Gate Design

The gate should live in `scripts/agent_job_contract.py`, not in runtime code.
That script already owns task-card validation, allowed diff checks, and report
artifact closeout checks, so it is the narrowest control-plane place to enforce
whether a task card's report artifacts can support a terminal `DONE` claim.

The Stop hook should call the contract check for active task cards. The hook can
warn on Stop/SessionEnd without blocking terminal exit, and can keep BeforeTool
behavior focused on allowed-file drift. This adds pressure at closeout without
touching greyhound runtime or Tenn product/runtime/data/extraction paths.

The check should infer "runtime-like" from task-card metadata and body text
using conservative keywords such as runtime, daemon, extraction, automation,
ingestion, scheduler, service, pipeline, product, and data. It should exempt
explicit `report-only` and `docs-only` scopes. For runtime-like cards, report
artifacts must include the Runtime Functionality Proof fields or avoid `DONE`.
If intended live output proof is missing, accepted terminal statuses are
`PARTIAL`, `BROKEN`, `DATA_MISSING`, or `DONE_WITH_RISK`.
