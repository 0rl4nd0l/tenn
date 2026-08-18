# Skill Checks

## Skill Count

Command:

```bash
find .agents/skills -maxdepth 2 -name SKILL.md | sort
```

Result:

```text
.agents/skills/codex-worker-bridge/SKILL.md
.agents/skills/tenn-explain/SKILL.md
.agents/skills/tenn-financial-metric-extraction/SKILL.md
.agents/skills/tenn-fix/SKILL.md
.agents/skills/tenn-git-guard/SKILL.md
.agents/skills/tenn-goal-report/SKILL.md
.agents/skills/tenn-handoff/SKILL.md
.agents/skills/tenn-improve-codebase-architecture/SKILL.md
.agents/skills/tenn-issue/SKILL.md
.agents/skills/tenn-review-board/SKILL.md
```

Count: 10.

## Frontmatter And H1

All ten repo-backed skill files were read. Final automated frontmatter/H1 check is recorded in `VALIDATION.md`.

## Repo Tracking And Ignore Behavior

`.agents/skills/tenn-fix/SKILL.md` and `.agents/skills/codex-worker-bridge/SKILL.md` are tracked files in this worktree.

`reports/` is ignored by git info exclude and must be force-added when report bundles are preserved.

## Skill Sync Dry Run

Command:

```bash
scripts/sync_codex_skills.sh
```

Result:

```text
would_link: 10
linked: 0
skipped: 0
```

No host-global sync was performed.
