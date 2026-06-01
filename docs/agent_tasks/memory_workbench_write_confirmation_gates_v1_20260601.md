---
job_id: memory_workbench_write_confirmation_gates_v1_20260601
lane: Memory
supporting_lanes:
  - Reporting
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md
  - docs/claude/STATE.md
  - cockpit-ui/components/cockpit/memory/memory-screen.tsx
  - cockpit-ui/components/cockpit/memory/memory-screen.test.tsx
  - cockpit-ui/lib/memory-write-routes.test.ts
  - cockpit-ui/app/api/cockpit/memory/_write-intent.ts
  - cockpit-ui/app/api/cockpit/memory/company/add/route.ts
  - cockpit-ui/app/api/cockpit/memory/company/expire/route.ts
  - cockpit-ui/app/api/cockpit/memory/market/add/route.ts
  - cockpit-ui/app/api/cockpit/memory/market/expire/route.ts
  - cockpit-ui/app/api/cockpit/memory/thesis/proposals/route.ts
  - cockpit-ui/app/api/cockpit/memory/thesis/proposals/[proposalId]/confirm/route.ts
  - cockpit-ui/app/api/cockpit/memory/thesis/proposals/[proposalId]/reject/route.ts
  - cockpit-ui/app/api/cockpit/memory/thesis/proposals/[proposalId]/apply/route.ts
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_endpoints.py
  - reports/agent_jobs/memory_workbench_write_confirmation_gates_v1_20260601/README.md
  - reports/agent_jobs/memory_workbench_write_confirmation_gates_v1_20260601/status.json
  - reports/agent_jobs/memory_workbench_write_confirmation_gates_v1_20260601/validation.json
  - reports/agent_jobs/memory_workbench_write_confirmation_gates_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_workbench_write_confirmation_gates_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_and_pr
related_issue: 154
operator_approval_source: "User requested ongoing safe GitHub issue remediation with isolated branches/worktrees; issue #154 is state:ready and requires this task card."
---

# Memory Workbench Write Confirmation Gates V1

## Objective

Add explicit user confirmation and route-specific intent evidence for Cockpit
Memory Workbench write paths without mutating production data, weakening memory
ownership, or creating any frontend-authoritative memory store.

The work is bounded to issue #154 and the following write paths:

- company memory add
- company memory expire
- sector memory add
- sector memory expire
- macro memory add
- macro memory expire
- safe qualitative edit through expire plus add
- thesis proposal create
- thesis proposal confirm
- thesis proposal reject
- thesis proposal apply

## Session Declaration

Agent: Codex

Branch: `safe/memory-workbench-write-confirmation-gates-v1-20260602`

Worktree:
`/home/l4nd0/tenn-memory-workbench-write-confirmation-gates-v1-20260602`

Lane: Memory

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, Memory Workbench UI, focused memory BFF route
guard, focused frontend/BFF tests, backend context route validation, focused
backend context tests, `docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: no path from the AGENTS.md contested-surface list,
but backend memory/thesis mutation routes and Cockpit memory UI are
trust-sensitive.

Collision risk: MEDIUM after current registry evidence shows no active jobs.
Proceed only after validation, active-job check, overlap check, and registry
claim.

Decision: proceed in the isolated worktree after gates pass.

## Contract Check

Target system layers: Client/orchestration and backend API validation around
the Memory boundary.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§1.2 Cockpit client/orchestration role, §2 mandatory flow, and §5 retrieval
authority boundaries. Memory writes must remain backend-authoritative and
separate from canonical financial truth.

What must not change: canonical financial truth, extraction/parser routing,
prompts, gold labels, database or Qdrant data, production memory contents,
runtime/model/GPU/service config, direct Cockpit-owned memory stores, and the
user-thesis proposal -> confirm -> apply state machine.

Why safe: the change adds fail-closed confirmation/intent checks before
existing backend-owned memory write handlers can mutate durable stores. It does
not introduce alternate storage or authoritative reads, and tests use mocks or
in-memory fakes rather than production data.

GPU process check required: no. This task does not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --repo-root .`
- Focused backend context negative-path tests proving missing/incorrect intent
  is denied before side effects.
- Focused BFF tests proving missing/incorrect intent is denied before proxy
  fetch.
- Focused Memory Workbench UI tests proving visible confirmation is required
  before mutation submission.
- Targeted frontend/backend lint or type checks where practical.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_workbench_write_confirmation_gates_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.

## Hard Stops

- Exact duplicate tracker or PR found.
- Unresolved HIGH collision risk on Memory Workbench or memory/thesis routes.
- Production data access or direct production memory-store mutation required.
- Implementation would bypass backend authority or create a frontend memory
  store.
- Financial-truth/source-evidence boundaries would need to be weakened.
- Validation fails without explanation.
