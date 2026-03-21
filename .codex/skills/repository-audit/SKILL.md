---
name: repository-audit
description: Runs the repository audit workflow for this repo. Use when the user asks for a repository audit, branch inventory or reduction analysis, environment preflight before validation, or an evidence-based completeness review.
---

# Repository Audit

Use this skill for full-repository audit requests in this workspace.

## Read First

- `.cursor/agents/repository_audit.md`
- `AGENTS.md`
- `README.md`
- relevant `docs/` files for the area being audited

## Workflow

1. Run the mandatory environment preflight defined in `.cursor/agents/repository_audit.md`.
2. If preflight is blocked, stop functional validation and return `DATA_MISSING`.
3. Inventory repository structure, tooling, branches, docs, rules, validation commands, and feature surfaces.
4. Compare branches against the default branch and identify duplicate, stale, or half-integrated work.
5. Run the smallest real checks the verified environment supports and record exact commands plus outcomes.
6. Separate `CONFIRMED`, `INFERRED`, and `UNVERIFIED` claims in the report.

## Constraints

- Do not claim functional validation results unless preflight is `READY`.
- Do not modify functional code while auditing unless the user explicitly asks for audit artifacts to be updated.
- Follow the required markdown sections and JSON schema from `.cursor/agents/repository_audit.md`.

## Output

Follow the evidence requirements from `.cursor/agents/repository_audit.md`, but default the user-facing response to normal prose/markdown sections rather than raw JSON. Only emit raw JSON if the user explicitly asks for JSON.
