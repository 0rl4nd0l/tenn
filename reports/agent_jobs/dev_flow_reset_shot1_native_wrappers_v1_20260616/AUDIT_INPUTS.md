# Audit Inputs

The Shot 1 implementation was based on the authoritative audit bundle at:

`reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/`

Files read before implementation:

- `README.md`
- `SKILLS_MATRIX.md`
- `TARGET_ARCHITECTURE.md`
- `GIT_HYGIENE_INTEGRATION.md`
- `OPERATOR_WORKFLOW.md`
- `IMPLEMENTATION_SEQUENCE.md`
- `OWNER_DECISIONS.md`

Key decisions adopted:

- Keep existing `diagnose`; wrap it through `tenn-issue`.
- Add first-class Tenn wrappers for `/issue`, `/review-board`, `/fix`,
  `worker`, `/explain`, `code-reviewer`, `/improve-codebase-architecture`, and
  `tenn-git-guard`.
- Fold Scribe into `STATE.md`, `DECISIONS.md`, and operator notes.
- Fold Frame Design into `/issue` and `/fix` templates.
- Fold Auto-progress into `/issue` as candidate ranking.
- Represent Git Hygiene as the quiet `tenn-git-guard` backend.
- Do not delete old skills in Shot 1.
