# Domain Docs

Tenn does not currently rely on a generic root `CONTEXT.md` or `docs/adr/`
layout for agent orientation. Generic skills that ask for domain docs should use
the Tenn source-of-truth stack below.

## Read First

Read these in order when relevant:

1. `AGENTS.md` for repo constitution, safety boundaries, and current source of
   truth hierarchy.
2. The active task card under `docs/agent_tasks/`, when one exists.
3. Relevant repo-backed skills under `.agents/skills/`.
4. `docs/entrypoints.md` only for runtime entrypoint work.
5. Current reports under `reports/agent_jobs/` for evidence and closeout.
6. Relevant GitHub issues or PRs using read-only commands first.

If a generic skill expects `CONTEXT.md`, treat that as absent unless the file
exists in the current checkout. Do not create `CONTEXT.md`, `CONTEXT-MAP.md`, or
ADRs as setup boilerplate.

## Tenn Terms

- **Issue**: GitHub tracker for backlog and coordination.
- **Task card**: execution contract, usually under `docs/agent_tasks/`.
- **Report**: evidence bundle and closeout under `reports/agent_jobs/`.
- **Lane**: work area such as Evaluation, Financial Truth, Provenance, Query
  Orchestration, Memory, or Reporting. Repo Hygiene is usually a supporting
  lane unless the validator accepts it as primary.
- **Mutation mode**: task-card classification such as `audit_only`,
  `safe_extension`, or `blocked`.
- **Financial Truth**: high-risk canonical financial metric work. Values must
  be source-bound, deterministic, auditable, and provenance-linked.

## Domain Guardrails

For extraction and financial truth work, do not treat narrative disclosures,
LLM output, or generic summaries as canonical numbers. Use source-bound parser,
scorecard, PDF, and provenance evidence.

For runtime or data work, do not start services or mutate DB, Qdrant, Redis,
news stores, memory, source PDFs, backfills, model/GPU config, or production data
unless the user explicitly approves that exact action.

If evidence is missing or stale, write `DATA_MISSING` rather than filling gaps
from memory or assumptions.
