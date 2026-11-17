# Agent Instruction Load Map

## Default-Loaded Or Near-Default Surfaces

| Agent or workflow | Default / near-default surfaces | Notes |
| --- | --- | --- |
| Codex in this repo | Session/developer instructions, user-provided `AGENTS.md`, repo `CLAUDE.md`, `SYSTEM_CONTRACT.md` for implementation, current task card when present, Codex memory when relevant. | `CODEX.md` exists but is a repo identity doc; current Codex runtime may receive AGENTS content directly from the user/session rather than automatically loading CODEX.md. |
| Claude Code | `CLAUDE.md`, imported `AGENTS.md`, `.claude/settings.json` hooks, Claude memory index. | Claude has the richest always-on hook surface and the strongest STATE update instruction. |
| Gemini CLI | `GEMINI.md`, then `CLAUDE.md` and `AGENTS.md`, `.gemini/settings.json` hooks. | Gemini has a conflicting graphify update instruction relative to shared AGENTS/CLAUDE policy. |
| Task-card jobs | Task card frontmatter/body, `scripts/agent_job_contract.py`, `scripts/agent_job_registry.py`, active registry records, report artifacts. | Task cards are execution contracts and should stay concise and exact. |
| GitHub issue work | GitHub issue body/comments, `.github/ISSUE_TEMPLATE/*.yml`, `docs/process/github_issue_system_protocol.md`, issue skills when triggered. | Issues are live backlog; reports and memory support them but do not replace them. |

## On-Demand Surfaces

| Surface | Load trigger | Recommendation |
| --- | --- | --- |
| `.claude/commands/*.md` | Explicit Claude command or matching task. | Keep on-demand. Do not copy command details into AGENTS.md. |
| `.claude/skills/**` | Matching specialized task. | Keep on-demand and tool-specific. |
| `.codex/skills/**` | Matching Codex skill trigger. | Keep on-demand; repo-local skills should not become default context. |
| `docs/process/codex_skill_sources/github_issue_system/**` | Issue closeout/finder/resolution-review work or mirror-sync audit. | Treat as repo-visible mirrors of local skills. |
| `docs/agent_tasks/**` | Specific task execution or historical audit. | Do not bulk-load; load exact task card(s). |
| `reports/agent_jobs/**` | Evidence verification, closeout, or follow-up linkage. | Reports are evidence artifacts, not standing instructions. |
| `docs/claude/STATE.md` | Current workstream status, when not owned by another active job. | Read for current state; write only when allowlisted and collision-free. |
| `graphify-out/**` | Architecture/codebase question and graphify files exist. | Current worktree has no graphify output; mark `DATA_MISSING`. |

## Load-Reduction Principle

Stable safety and architecture invariants belong in `SYSTEM_CONTRACT.md`,
`AGENTS.md`, and the agent-specific identity files. Task-specific procedures
belong in skills, issue templates, task cards, protocol docs, and reports. The
next docs patch should remove or map contradictions rather than copying more
workflow detail into default-loaded files.
