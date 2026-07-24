# Tenn Codex X Extraction Programme Supervisor

## Objective

Reconcile the completed Tenn extraction specification and ticket set against
fresh canonical and live pull-request evidence, then prepare a thin,
restartable Codex X run package without changing extraction code or launching
a child.

## Current state

`WAITING_ON_USER`

The orchestration design contract is present, but the Tenn extraction workspace,
specification, ADRs, and ticket files were not found. The ticket inventory,
ticket hashes, complete reconciliation, execution order, and exact first child
prompt therefore cannot be produced without inventing or rewriting planning
inputs.

## Canonical identity

- Repository: `0rl4nd0l/tenn`
- Live extraction canonical branch:
  `migration/clean-runtime-baseline-reconstruct-v1`
- Canonical commit: `2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7`
- Canonical tree: `cba105b2ff945fb0279158c7f54de2bcf4517e5d`
- Commit subject: `fix(runtime): resolve llama symlink library path (#518)`
- Evidence: remote branch resolution, fresh fetch, live PR bases, and
  ancestry checks
- GitHub default branch `main` is not the extraction canonical line for this
  programme: its current SHA `cc99cec1bfc4ee79aac407a8caeed8d4baec2f6b`
  does not contain PR #517.

## Design contract

Read-only source:
`/home/l4nd0/codex-x-orchestrator-design`

Used:

- `ORCHESTRATOR_SPEC.md`
- `TRANSITIONS.md`
- `PROMPT_TEMPLATES.md`
- `RESTARTABILITY_TEST.md`
- `CLEAN_EXPORT_GATE.md`
- `schemas/run_manifest.schema.json`
- `schemas/ticket_state.schema.json`
- `schemas/child_result.schema.json`
- `schemas/review_result.schema.json`
- `schemas/integration_result.schema.json`

The simulator was neither executed nor modified.

## Reconciliation result

See:

- [RECONCILIATION.md](RECONCILIATION.md)
- [RECONCILIATION_LEDGER.json](RECONCILIATION_LEDGER.json)
- [ARTIFACT_HASHES.json](ARTIFACT_HASHES.json)
- [RUN_PACKAGE_PROPOSAL.md](RUN_PACKAGE_PROPOSAL.md)
- [FIRST_CHILD_PROMPT.md](FIRST_CHILD_PROMPT.md)

Known current work is sealed as follows:

- PR #517 is merged and contained in canonical. Any ticket whose behavior is
  current-period source-column binding must be classified `SUPERSEDED` or
  `DONE` after exact ticket comparison.
- PR #508 is an open draft with successful checks and owns NPAT owner
  attribution and OCI-boundary behavior. Any matching ticket is
  `OVERLAPS_EXISTING`.
- PR #513 is an open draft with successful checks and owns declarative
  metric-contract authority. Any matching ticket is `OVERLAPS_EXISTING`.

No extraction ticket was classified `READY`, because the ticket set is absent.
No execution order or child assignment was started.

## Constraints and unsafe actions avoided

- No product, extraction, test, source, gold-label, prompt, runtime, data,
  service, queue, store, model, GPU, deployment, or merge action was taken.
- No pull request was modified.
- No `codex-x` child was launched.
- No simulator or orchestration infrastructure was executed or changed.
- No old planning file was promoted to current repository truth.
- No ticket was invented from a PR title or historical report.
- The stale/default `main` branch was not treated as canonical.

## Evidence used

- Fresh remote identity for `0rl4nd0l/tenn`.
- Live GitHub metadata, commits, changed paths, and checks for PRs #508,
  #513, and #517.
- Fresh canonical ancestry checks.
- Read-only Tenn Git Guard preflight and task-ledger/registry evidence.
- Local filesystem search and a bounded connected-Drive search for the named
  extraction programme.
- The read-only Codex X orchestration design contract listed above.

## Files touched

Only this report package under
`reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/`.

## Files intentionally not touched

- All product and extraction source files.
- `AGENTS.md`, `.codex/`, hooks, policies, workflows, and automation controls.
- `/home/l4nd0/codex-x-orchestrator-design/**`.
- PR #508 and PR #513 branches and worktrees.
- The merged PR #517 worktree.

## Validation status

- Canonical remote fetch and identity: `PASS`.
- PR state/head/base/check inspection: `PASS`.
- PR #517 ancestry in canonical: `PASS`.
- Design-contract SHA-256 inventory: `PASS`.
- Extraction spec/ticket inventory: `DATA_MISSING`.
- JSON parse and report diff checks: `PASS`.
- Runtime functionality: `DATA_MISSING`, by owner boundary.

## Commands and exits

- Local Git identity/status/upstream inspection: exit `0`.
- `git ls-remote --symref origin HEAD` and named branch lookup: exit `0`.
- Fresh fetch of `origin/main` and
  `origin/migration/clean-runtime-baseline-reconstruct-v1`: exit `0`.
- PR #517 ancestry in extraction canonical: exit `0`.
- PR #517 ancestry in `main`: exit `1` as expected.
- Portable Git Guard with full fallback detail: exit `1` after its bounded
  `git branch -a` subprocess timed out.
- Portable Git Guard with summary fallback: exit `0`, final decision `pass`.
- Live GitHub PR inspection: exit `0`.
- Initial `gh pr view` request used one unsupported JSON field and exited
  non-zero; the corrected query exited `0`.
- Local and connected-document artifact searches: completed with no matching
  extraction spec/ticket package.

## Raw logs

No product or child logs were generated. Concise evidence is embedded in this
report package; the current supervisor session retains command output.

## Ignored and untracked artifact note

No child delta exists, so dependency classification has not started. The future
clean-export gate must reject every ignored or untracked required dependency.
This report branch began from a clean exact-canonical worktree.

## Approvals needed

No approval is needed to continue read-only reconciliation once the missing
artifact path is supplied. Runtime/data/backfill/re-extraction, source PDFs,
gold labels, prompts, stores, services, merge, and deployment remain separately
owner-authorized transitions.

## Remaining risk

The absent ticket set prevents exact scope comparison. Mapping tickets from PR
titles or older repository plans would risk duplicating canonical work,
overlapping unresolved drafts, and changing the completed programme plan.

## Waiting protocol

`WAITING_ON_USER`

Needed: exact local path or accessible URL for the completed Tenn extraction
workspace containing the spec, ADRs, and ticket files.

Why: this unlocks hashing, complete ticket-by-ticket reconciliation, the first
`READY` selection, valid run-manifest construction, ticket-state planning, and
the exact first bounded child prompt.

Current safe state: canonical and live PR boundaries are sealed; a clean
report-only supervisor worktree and blocked ledger exist; no child or product
work started.

Options: provide the workspace root; provide the spec plus ticket/ADR paths; or
state that the artifacts were not persisted and explicitly authorize a
different planning recovery lane.

Recommended: provide the existing workspace root so the completed plan remains
authoritative.
