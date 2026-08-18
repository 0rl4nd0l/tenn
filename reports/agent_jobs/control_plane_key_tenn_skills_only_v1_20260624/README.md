# Control Plane Key Tenn Skills Only V1

Status: implementation complete, validation passed

This report records the repo-local skill-surface trim and follow-up expansion
requested on
2026-06-24. Scope is limited to Tenn control-plane skill entrypoints, docs, task
card, and this report bundle.

Host-global skill roots are intentionally not modified.

## Result

Retained visible repo-local `.agents` skills:

- `.agents/skills/caveman/SKILL.md`
- `.agents/skills/codex-worker-bridge/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-financial-metric-extraction/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `.agents/skills/tenn-review-board/SKILL.md`
- `.agents/skills/tenn-handoff/SKILL.md`
- `.agents/skills/tenn-explain/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-improve-codebase-architecture/SKILL.md`
- `.agents/skills/tenn-issue/SKILL.md`
- `.agents/skills/zoom-out/SKILL.md`

Removed visible repo-local legacy/custom entrypoint:

- `.codex/skills/cockpit-flag-orchestrator/SKILL.md`

The legacy cockpit skill support files under `.codex/skills/cockpit-flag-orchestrator/`
were also removed so that `.codex/skills` no longer exposes a repo-local
`SKILL.md`.
