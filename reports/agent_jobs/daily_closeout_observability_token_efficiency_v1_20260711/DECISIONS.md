# Decisions

## Source Of Truth

The preserved Shot 1 `DECISIONS.md`, `APPROVAL_MANIFEST.md`, and
`IMPLEMENTATION_PLAN.md` remained the accepted design. Shot 2 did not widen
into deployment, live proof, other automation jobs, UI, database, or retention.

## Publication Decision

- USER_APPROVED: Publication Group P only on 2026-07-11.
- One coherent exact-allowlist commit, push of the existing task branch, and a
  draft PR are authorized.
- Merge, deployment, execution-worktree reconciliation, systemd, live model,
  scheduled proof, runtime/data/extraction/model mutation, and retention remain
  separate unapproved groups.

## Implementation Decisions

- Keep daily-closeout observability in one standard-library module and keep
  runner integration narrow.
- Use atomic owner-only storage, symlink refusal, immutable terminal/evidence/
  review interfaces, per-job locking, stale-run recovery, and artifact hashes.
- Bound probes to fixed argument arrays and timeouts, 8 KiB per probe, 32 KiB
  evidence packs, 32 KiB raw structured model output, eight findings, four
  targeted reads, and 8 KiB rendered reports.
- Compare normalized facts and use a native zero-token path for no-change and
  deterministic transitions.
- Record model-gate reasons and actual invocation separately; never retry or
  escalate automatically.
- Treat Codex output as ephemeral/untrusted, require the versioned output
  schema, validate it again locally, require known fact references, and reject
  unsafe next actions.
- Keep dollar cost `DATA_MISSING` until an applicable billing source is
  verified; never substitute public API pricing.
- Join reviews immutably at read time and summarize the latest seven completed
  runs without mutating original records.

## Review-Driven Fixes

- Moved the first orchestration draft out of the shared runner into the
  dedicated observability module, leaving a narrow runner adapter.
- Added recognition of the new failure-report shape to native health checks.
- Preserved actual-model-invoked provenance on terminal failures.
- Tightened local output validation to every V1 schema constraint.
- Added a 32 KiB pre-load model-output cap and symlink refusal while preserving
  invalid/oversized output for review.

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked: `docs/dev/automation_index.md`, Shot 1 packet, four V1 schemas
- docs_changed: `docs/dev/automation_index.md`, four V1 schemas
- docs_followup: deployment/scheduled proof only after their approval groups
- stale_docs_discovered: none

## Model, Worker, Ledger, And Registry

- task_tier: `large`
- actual_model: current Codex session model; deployment identifier
  `DATA_MISSING`
- subagents_used: none; not requested and not needed for bounded integration
- registry: `PASS`, zero active jobs
- ledger: `PASS`, 311 entries across live and committed sources
- duplicate work: `NO_MATCHING_ACTIVE_WORK_FOUND`
- live ledger append: skipped because the task card excludes live ledger
  mutation; `ledger_entry.json` records the intended transition
