# Owner Decisions

These are decisions for Orlando or a later review-board, not changes made in
this audit.

## Decisions Needed

| Decision | Options | Recommended |
| --- | --- | --- |
| Daily operator command set | Keep all visible skills, or narrow to `/issue`, `/fix`, `/review-board`, `/explain`, `/goal`, `/handoff`. | Narrow to the six-command set. |
| `tenn-auto-progress` | Keep visible, delete, or fold into `/issue`. | Fold into `/issue` as internal candidate ranking. |
| `tenn-frame-design` | Keep as skill, delete, or rehome into templates. | Rehome schema into templates and optional `/goal` frame mode. |
| `tenn-git-hygiene` | Keep separate, merge fully into git guard, or split reference vs command. | Keep explicit hygiene audit only; move common guard content to `tenn-git-guard`. |
| `tenn-handoff` | Host-only, repo-native skill, or both. | Both: repo-native `tenn-handoff` for reports/templates plus host temp handoff fallback. |
| Legacy `.codex/skills/cockpit-flag-orchestrator` | Grandfather, rehome, deprecate, or delete later. | Deprecate as active default; rehome safe flag-triage ideas later if still needed. |
| Host Tenn issue skills | Leave host-only, mirror into repo, or wrap selected pieces. | Leave host-only for now; wrap only if repeated repo workflows need them. |
| Docs freshness | Prose-only, template fields, or script plus fields. | Template fields now, future `scripts/docs_impact.py` after ledger/handoff work settles. |
| Model routing | Implicit, task-card fields, or separate router skill. | Task-card/worker/review fields first; no standalone user-facing skill. |
| Plugin skill visibility | Document all plugin skills in Tenn, or hide behind domain triggers. | Hide behind explicit domain/plugin triggers. |

## Decisions Not Needed For This Report

- No decision is needed to delete or edit skills now; this audit made no such
  changes.
- No GitHub issue/PR mutation is needed unless Orlando wants to preserve the
  report bundle in a branch/PR.
- No product/runtime/data/extraction decision is needed.

## Suggested Owner Approval Surface For Next PR

Approve a narrow control-plane implementation PR that may edit:

- selected `.agents/skills/*/SKILL.md`
- selected `docs/dev_flow/templates/*`
- `docs/agents/skill-registry.md`
- maybe `scripts/docs_impact.py` only if implementation is explicitly approved
- one task card and report bundle

Do not approve branch cleanup, skill deletion, host-global mutation, product
code, or GitHub writes as part of that same PR.
