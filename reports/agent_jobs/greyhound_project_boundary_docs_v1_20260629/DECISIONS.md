# Decisions

## Boundary Decision

Decision: codify Greyhound as an external sibling project in Tenn
docs/control-plane routing.

Rationale: the review board concluded that Tenn and Greyhound should remain
separate repositories, working roots, runtime ownership surfaces, and
agent/report lanes. Greyhound should not be treated as a Tenn subsystem merely
because current filesystem paths include `tenn`.

## Implementation Decision

Decision: add `docs/dev_flow/PROJECT_BOUNDARIES.md` and add a source-map row in
`docs/README.md`.

Rationale: the focused doc is the durable operating rule; the source-map row
keeps the doc discoverable under the existing documentation navigation
contract.

## Scope Decision

Decision: do not touch Tenn runtime/product/extraction code and do not touch
Greyhound repo/runtime/service/GitHub surfaces.

Rationale: the requested shot is docs-only. Physical Greyhound relocation is a
separate owner-approved runtime-proof workstream.

## Canonical Drift And Publish Decision

Decision: after owner approval to proceed with publication, rebase the single
docs commit onto the current canonical ref before pushing and opening a draft
PR.

Evidence: read-only overlap checks showed no changes from the new canonical ref
to this task's allowed files:

- `docs/README.md`
- `docs/dev_flow/PROJECT_BOUNDARIES.md`
- `docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md`

Rationale: the worktree was clean after the local commit, the overlap check was
empty, and the user explicitly approved the commit/push/PR path. Rebasing the
single docs commit removed the stale-path blocker without touching runtime or
Greyhound surfaces.

## Closeout Correction Decision

Decision: update the report-local closeout and provenance wording after review
found stale publication-wait language.

Evidence before this closeout correction: PR #472 was open as a draft against
`migration/clean-runtime-baseline-reconstruct-v1`, head
`7af1c2dceaa91b5d0f3ff7e1751d690902f3e5da`, merge state `CLEAN`, with
`lint-and-test` and `scan` successful. The old missing-hook-tool wait state was
resolved by owner-approved one-shot push using
`TENN_ALLOW_MISSING_HOOK_TOOLS=1`.

Rationale: report artifacts are part of the committed diff and must match live
publication state before this PR can be treated as review-ready. The correction
does not change Tenn runtime/product/extraction code or Greyhound-owned
surfaces.

## Docs Impact Check

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`,
  `.agents/skills/tenn-fix/SKILL.md`,
  `/home/l4nd0/tenn/reports/agent_jobs/tenn_greyhound_repo_separation_review_board_20260629T175721+1000/`
- `docs_changed`: `docs/dev_flow/PROJECT_BOUNDARIES.md`, `docs/README.md`
- `docs_followup`: `none` for docs-only boundary routing; separate Greyhound
  relocation manifest remains a different workstream if desired.
- `reason`: task changed agent/operator routing boundaries and therefore
  required durable docs.

## Model And Worker Routing

- `task_tier`: `small` for implementation; source review board was `critical`
  because physical relocation and runtime ownership were considered there.
- `recommended_model`: standard coding model.
- `actual_model`: GPT-5 Codex.
- `why_this_model`: small docs/control-plane patch with exact allowlist after a
  prior high-risk review board.
- `worker_model_allowed`: false for this shot.
- `worker_decision_limit`: no workers used; final scope and closeout retained
  by Codex in the Tenn task worktree.
- `escalation_needed`: false for docs-only change; true for any physical
  Greyhound relocation.
