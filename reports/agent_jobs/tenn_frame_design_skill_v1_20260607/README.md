# Tenn Frame Design Skill V1

## Objective

Create a Tenn-native control-plane skill for long-running `/goal` work that
requires a compact execution Frame, durable state tracking, operator steering
capture, and an optional Scribe pattern.

## Files Changed

- `docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md`
- `.agents/skills/tenn-frame-design/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `reports/agent_jobs/tenn_frame_design_skill_v1_20260607/README.md`

## Current Evidence

- Worktree: `/home/l4nd0/tenn-frame-design-skill-v1-20260607`
- Branch: `safe/tenn-frame-design-skill-v1-20260607`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`
- Origin branch readback:
  `origin/migration/clean-runtime-baseline-reconstruct-v1` =
  `10c162a5162b3e5fc1306cdd908b23bfa6f0a5a8`
- Read-only registry:
  `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  returned `ok=true`, `read_only=true`, `lock_acquired=false`, and
  `active_jobs=[]`.
- The source checkout at `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  was dirty and on `tmp/sloppy-fix-demo`, so edits were made in a clean sibling
  worktree.
- The original shell cwd was the unrelated greyhound repo, which did not have
  the requested Tenn remote branch.

## Product Readiness Rationale

This supports Tenn product readiness indirectly by improving how long-running
product work is framed, steered, and reported. The skill makes agents preserve
the real objective, carry non-negotiables forward, record user corrections, and
stop cleanly on conflicts or missing evidence before product/runtime/data
surfaces are touched.

## Exact Frame Schema

```markdown
# Frame

## Objective
<one concrete objective, preserving the user's real goal>

## Why This Matters
<short Tenn-specific reason this work matters>

## Non-Negotiables
- <hard boundary or invariant>

## Judgement Rules
- <rule for deciding scope, tradeoffs, readiness, or stop conditions>

## Scope In
- <included surface>

## Scope Out
- <excluded surface>

## Evidence Sources
- <current repo, task card, registry, report, issue, runtime, or user evidence>

## Success Shape
- <what a good completed state looks like>

## Stop States
- <condition that requires stopping, waiting, or reporting DATA_MISSING>

## Steering Log
- <YYYY-MM-DD HH:MM TZ> - <user correction, invariant, preference, or decision>
```

## Scribe Boundaries

- Scribe is optional and used only when requested or when live steering may be
  lost during a long `/goal` run.
- Scribe monitors user corrections, guardrails, invariants, preferences, and
  decisions.
- Scribe writes compact notes to `OPERATOR_NOTES.md` or `FRAME.md` steering log.
- Scribe interrupts only for conflicts, safety issues, ambiguous permission, or
  a correction that invalidates the current Frame.
- Scribe never implements code and never mutates product, runtime, data,
  extraction, registry, GitHub, memory, DB, Qdrant, news, services, prompts,
  model/GPU config, source PDFs, or gold labels.

## Validation Commands

- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Exit status: 0
  - Result: `ok=true`, `read_only=true`, `lock_acquired=false`,
    `active_jobs=[]`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md`
  - Exit status: 0
  - Result: `ok=true`
- `python3 - <<'PY' ... frontmatter parser for .agents/skills/*/SKILL.md ... PY`
  - Exit status: 0
  - Result: parsed `tenn-financial-metric-extraction`, `tenn-frame-design`,
    `tenn-goal-report`, and `tenn-task-card-registry-safety`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md --no-write-report`
  - Exit status: 0
  - Result: `ok=true`; changed files were exactly:
    `.agents/skills/tenn-frame-design/SKILL.md`,
    `.agents/skills/tenn-goal-report/SKILL.md`,
    `docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md`, and
    `reports/agent_jobs/tenn_frame_design_skill_v1_20260607/README.md`.
- `git diff --check --cached && git diff --check`
  - Exit status: 0
  - Result: no whitespace errors in staged or unstaged diff
- `git status --short --untracked-files=all`
  - Exit status: 0
  - Result:
    - `A  .agents/skills/tenn-frame-design/SKILL.md`
    - `M  .agents/skills/tenn-goal-report/SKILL.md`
    - `A  docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md`
    - `A  reports/agent_jobs/tenn_frame_design_skill_v1_20260607/README.md`

## Unsafe Actions Avoided

- No product/backend/frontend/runtime/data/extraction code was edited.
- No DB, Qdrant, news, memory, backfill, source PDF, gold label, prompt,
  service, runtime/model/GPU config, or production data was touched.
- No dependencies were installed.
- No GitHub issues or PRs were created, edited, commented on, closed, or
  reopened.
- No push, merge, rebase, reset, clean, stash, branch deletion, or parked-work
  mutation was performed.
- No Loopgen or third-party skill text was copied.
- The dirty Tenn baseline and unrelated greyhound checkout were not cleaned or
  absorbed.

## Next Recommended Product-Focused /goal Prompt

```text
/goal Use Tenn task-card/registry safety, tenn-frame-design, and
tenn-goal-report. Start by creating FRAME.md, STATE.md, and
OPERATOR_NOTES.md for exactly one live issue-backed Tenn product-readiness
blocker. Preserve product/runtime/data/extraction hard boundaries until the
task card and registry are clean. Then implement one narrow safe extension only
if the Frame evidence supports it; otherwise stop with DATA_MISSING or
WAITING_ON_USER and write the report.
```
