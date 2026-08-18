# Context Packs

## Pack 1 - Issue #291

Issue: https://github.com/0rl4nd0l/tenn/issues/291

Purpose: Build a Codex-native auto-progress workflow that turns issue/milestone
state into ranked candidates, compact context packs, task-card drafts, and
approval manifests.

Current evidence:

- State OPEN.
- M0 - Control Plane Hardening.
- Labels include `state:ready`, `priority:p1`, `risk:medium`,
  `type:automation`, and `type:control-plane`.
- Issue body defines Phase 1 as read-only planning and explicitly forbids
  default GitHub writes, pushes, production runtime/DB mutation, and multi-job
  execution.

Recommended next action: approve Phase 2 issue-to-card dry run for #281 only.

Hard stops: GitHub writes, source execution, commits, product/runtime/data
mutation, service starts, broad validation, or multiple candidate execution.

## Pack 2 - Issue #281

Issue: https://github.com/0rl4nd0l/tenn/issues/281

Purpose: Add a minimal lint/type gate for active backend/scripts so formatting
and import hygiene issues do not wait until runtime or review.

Current evidence:

- State OPEN.
- Labels include `lane:evaluation`, `lane:repo-hygiene`, `priority:p2`,
  `risk:medium`, `state:ready`, `type:validation-gap`.
- No milestone is assigned in the issue view.
- Body suggests a minimal `ruff` gate scoped to `financial-engine_v2/backend`
  and `financial-engine_v2/scripts`, with current isolated environment
  compatibility.

Planner read: strong Phase 2 dry-run target, but execution is product-adjacent
because it would touch validation configuration for backend/scripts. Phase 2
should draft a task card only.

Hard stops: dependency installs, broad tests, backend behavior changes, runtime
validation, service starts, product code edits, commits, GitHub writes.

## Pack 3 - Issue #234

Issue: https://github.com/0rl4nd0l/tenn/issues/234

Purpose: Classify stale dirty generated report artifact
`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`
so later agents can trust task-card diff checks.

Current evidence:

- State OPEN.
- M0 - Control Plane Hardening.
- Labels include `mode:audit`, `lane:repo-hygiene`, `lane:evaluation`,
  `priority:p2`, `risk:medium`, `state:ready`, `type:control-plane`,
  `type:validation-gap`.
- Issue body defines a report-only classification lane and forbids product,
  runtime, financial-truth, extraction prompt, gold-label, and data-store
  mutation.

Planner read: strong report-only candidate if Phase 2 chooses a repo-hygiene
classification instead of #281.

Hard stops: touching the historical artifact without explicit task-card
permission, product/extraction changes, destructive cleanup, or GitHub writes.

## Pack 4 - Issue #139

Issue: https://github.com/0rl4nd0l/tenn/issues/139

Purpose: Decide whether missing `.cursor/rules/*` architecture rule references
should be restored, replaced, or retired from agent workflows.

Current evidence:

- State OPEN.
- M0 - Control Plane Hardening.
- Labels include `mode:audit`, `priority:p1`, `risk:medium`,
  `state:data-missing`, `type:control-plane`, `type:docs`.
- Issue body records repeated `DATA_MISSING` architecture-rule evidence and a
  docs/safe-extension path if an owner chooses restore or retire.

Planner read: useful later, but not the best Phase 2 target because it requires
an architecture-owner decision before remediation.

Hard stops: conflicting with `SYSTEM_CONTRACT.md`, product/runtime/data changes,
or broad skill/doc rewrites without approval.
