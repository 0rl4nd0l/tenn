---
job_id: cockpit_home_strategy_lab_declutter_v1_20260525
lane: Reporting
owner: Codex
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525
allowed_files:
  - docs/agent_tasks/cockpit_home_strategy_lab_declutter_v1_20260525.md
  - reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/README.md
  - reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/status.json
  - reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/validation.json
  - reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/diff-check.json
  - reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/rendered-smoke.json
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - cockpit-ui/lib/strategy-lab-review-queue.ts
  - cockpit-ui/lib/strategy-lab-review-queue.test.ts
---

# Cockpit Home Strategy Lab Declutter v1

## Objective

Declutter Cockpit Home by reducing Strategy Lab / QuantDinger to a compact,
analyst-useful status summary while keeping repo-backed review and provenance
details available behind drilldown, artifact review, or debug/detail surfaces.

## Required Home Behavior

Home must show a compact Strategy Lab card with:

- status: Read-only sandbox proof verified
- current runtime: Offline
- review state: Pending review
- trading/execution: Disabled
- one-line value summary
- one visible blocker summary
- a visible "View details" and/or "Open Strategy Lab" affordance

Home must not show by default:

- full artifact path lists
- individual payload refs
- fixture rows
- export packet lists
- repeated safety labels
- historical smoke internals
- detailed review queue rows
- long DATA_MISSING lists

## Preservation Requirements

Do not remove or weaken:

- the repo-backed Strategy Lab / QuantDinger review subsystem
- review queue data
- experiment session envelope
- provenance labels
- DATA_MISSING semantics
- safety flags
- artifact routes

Detailed evidence must remain reachable outside the compact Home summary through
the Strategy Lab details view, artifact review page, expandable disclosure, or a
developer/debug detail surface.

## Forbidden

- Do not remove Strategy Lab subsystem data or delete evidence artifacts.
- Do not hide safety state entirely.
- Do not set `current_sidecar_available=true`.
- Do not set `execution_allowed=true`.
- Do not set `canonical_financial_truth=true`.
- Do not enable paper/live trading.
- Do not add runtime, Docker, QuantDinger startup, live transport, MCP, or backend adapter behavior.
- Do not write Tenn DB, Qdrant, news, memory, canonical truth, or production data.
- Do not touch parser, runtime, model, GPU, dependency, or service config.
- Do not clean, absorb, stage, or mutate unrelated dirty task cards.

## Contract Boundaries

Target system layer: Client presentation layer only.

Relevant contract rules:

- `SYSTEM_CONTRACT.md` section 1.1: backend remains the sole authority.
- `SYSTEM_CONTRACT.md` section 1.2: Cockpit remains a client and orchestration layer.
- `SYSTEM_CONTRACT.md` section 1.3: Cockpit must not implement retrieval.
- `SYSTEM_CONTRACT.md` section 2: no layer skipping or duplicate pipeline.
- `SYSTEM_CONTRACT.md` sections 3 and 4: no fabricated financial truth, no data mutation.

What must not change:

- backend authority, retrieval, ingestion, extraction, storage, embeddings, and
  canonical financial truth
- QuantDinger availability, execution, trading, and sidecar transport flags
- persisted evidence artifacts and DATA_MISSING semantics

Why this is safe:

- the task is limited to UI summarization and focused tests over existing
  Strategy Lab data structures; it does not add runtime or data-store behavior.

GPU process check required: no. This task does not spawn, restart, or depend on
`llama-server`.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_strategy_lab_declutter_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_strategy_lab_declutter_v1_20260525.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_strategy_lab_declutter_v1_20260525.md`
- focused Vitest for Strategy Lab Home cards and Strategy Lab lib helpers
- TypeScript
- targeted ESLint
- API smoke if relevant
- rendered smoke if feasible
- forbidden-promotion grep
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_strategy_lab_declutter_v1_20260525.md`
- `python3 scripts/agent_job_registry.py release cockpit_home_strategy_lab_declutter_v1_20260525`
- final git status

## Deliverables

- compact Strategy Lab Home summary card
- detail/disclosure path that still exposes proof and review artifacts
- focused tests proving forbidden promotion flags stay false and detailed
  evidence remains reachable outside the compact Home summary
- `reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/README.md`
- `reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/status.json`
- `reports/agent_jobs/cockpit_home_strategy_lab_declutter_v1_20260525/validation.json`
