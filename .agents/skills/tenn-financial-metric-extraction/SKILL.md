---
name: tenn-financial-metric-extraction
description: Use for issue-backed Tenn Financial Truth and PDF financial metric extraction work where canonical numbers, provenance, scorecards, parser behavior, or extraction gaps must be audited or changed under strict source-bound safety rules. Do not use for generic finance research or investing analysis.
---

# Tenn Financial Metric Extraction

Use this skill for Financial Truth work tied to live Tenn issues, task cards,
registry state, reports, source PDFs, parser output, or metric scorecards.

## Required Preflight

1. Verify repo path, branch, HEAD, origin, and dirty state.
2. Re-check the relevant GitHub issues read-only before relying on older issue
   context. Current blocker families usually include #73, #96, #97, and #286,
   but live evidence wins.
3. Validate or create a task card before edits. Keep allowed files exact.
4. Inspect active registry evidence safely. The current audit found
   `list-active --read-only` is missing; do not run lock-writing registry
   commands for read-only audit.
5. Decide whether the task is audit-only, report-local, or one narrow safe
   extension. If unclear, stop with `WAITING_ON_USER`.

## Financial Truth Rules

- Canonical values must be source-bound, deterministic, auditable, and
  provenance-linked.
- Do not use LLM output as canonical financial truth.
- Do not silently promote disclosure/narrative values into canonical metrics.
- Preserve metric ontology boundaries; do not widen canonical coverage just to
  improve a score.
- Prefer exact PDF/source evidence, parser rows, payloads, scorecards, and
  focused fixtures over qualitative claims.

## Forbidden Without Explicit Approval

- DB, Qdrant, news, memory, backfill, runtime, service, source-PDF, gold-label,
  prompt, model, GPU, or production-data mutation.
- Broad extraction rewrites, corpus-wide backfills, route changes, or ontology
  expansion.
- GitHub issue/PR write actions.

## Workflow

1. Build a current evidence packet: issue, task card, branch/dirty state,
   report artifacts, parser/scorecard files, and source references.
2. Classify the work:
   - `AUDIT_ONLY`: report findings and blockers only.
   - `REPORT_LOCAL`: create local evidence artifacts only.
   - `SAFE_EXTENSION`: one narrow source-bound code/doc/test change.
3. For fixes, make the smallest change that addresses the source-proven failure.
4. Validate with the cheapest focused check tied to the changed extraction
   contract. Do not run broad tests unless justified.
5. Report files touched, source evidence, validation, remaining
   `DATA_MISSING`, and the next safe prompt.
