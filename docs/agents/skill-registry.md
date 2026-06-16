# Tenn Skill Registry

`AGENTS.md` is the governing policy. This file labels skill-like surfaces so
agents do not rediscover authority every turn.

## Active Repo-Backed Codex Skills

Active Tenn repo-backed Codex skills live under:

```text
.agents/skills/<skill-name>/SKILL.md
```

Rules:

- The first H1 is required and identifies the skill.
- YAML frontmatter is optional metadata.
- If frontmatter exists, `name` must match the skill directory and
  `description` should be non-empty.
- Skill instructions must preserve task-card, registry, approval, and dirty-state
  boundaries from `AGENTS.md`.

## Legacy Or Tool-Specific Surfaces

- `.codex/skills`: legacy/custom Codex surface. Do not treat as active repo
  authority unless a current task card explicitly grandfathers a skill.
- `.claude/skills`: Claude-only reference/import surface.
- `.kilocode/skills`: Kilo Code-only reference/import surface.
- `docs/claude/skills`: reference docs, not active Codex policy.
- `docs/process/codex_skill_sources`: reference mirrors, not active policy.
- host `$CODEX_HOME/skills`: external state; never mutate without explicit user
  approval.

## Sync Policy

`scripts/sync_codex_skills.sh` is dry-run by default. It may link `.agents/skills`
into host `$CODEX_HOME/skills` only when run with `--apply` and when the current
task card and user approval explicitly allow host skill mutation.
