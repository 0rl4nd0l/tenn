# Gaps And Risks

## Decision-Relevant Gaps

No gap requires changing Phase 3C docs or tests before an implementation-plan-
only Phase 3E.

The following gaps must remain explicit in Phase 3E:

- Real QuantDinger sidecar capability is unconfirmed.
- Real MCP/API transport is unconfirmed.
- Production auth, token, timeout, retry, and network behavior are unconfirmed.
- Raw payload storage and quarantine persistence are not designed beyond local
  mock references.
- The contract is shape/test evidence, not runtime implementation.
- The Phase 3C tests are stdlib shape/policy checks, not `jsonschema`
  validation.

## Consolidation Risk

The Phase 2/3A/3B/3C worktrees are not cleanly consolidated:

- Phase 2 has untracked task-card/schema/fixture files.
- Phase 3A has staged additions under task-card, Strategy Lab docs, mock
  payloads, and reports.
- Phase 3B has untracked task-card, Strategy Lab docs, vectors, and tests.
- Phase 3C has untracked task-card, Strategy Lab docs, mock transport fixtures,
  and tests.

Risk: a future implementation-plan task could accidentally reason from files
that exist only in isolated dirty worktrees. Mitigation: Phase 3E must begin
with an explicit consolidation/readiness checkpoint and must not merge,
cherry-pick, or implement code unless separately authorized.

## Boundary Risks

- The class names in Phase 3C are design-only. Reusing them in code requires a
  new task card and a separate implementation plan.
- `export_artifact` is local mock conversion only and never persistence.
- Simulated timeout and sidecar-unavailable cases are not operational behavior.
- Valid artifacts are pending-review evidence only, not Tenn canonical financial
  truth.
- Negative fixtures intentionally contain invalid fields as rejection evidence.

## Risk Decision

Risk remains `LOW/MEDIUM` only while Phase 3E is implementation-plan-only.

Risk becomes `HIGH` and should stop if the next phase touches runtime/backend,
Cockpit, stores, parser/gold-label files, source-registry files, Docker,
systemd, env/secrets, dependency files, QuantDinger/MCP runtime, real API
clients, tokens, broker/exchange config, paper/live execution, or autonomous
loops.
