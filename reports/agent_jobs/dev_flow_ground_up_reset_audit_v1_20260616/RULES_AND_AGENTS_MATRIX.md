# Rules And Agents Matrix

| Surface | What It Does | Useful? | Overlap/Problem | Classification | Action |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | Stable Tenn constitution: target verification, evidence hierarchy, safety boundaries, task cards, registry, validation, GitHub rules. | Yes. | Long but still high-signal. | `CORE_KEEP` | Keep short and avoid adding command procedures. |
| `docs/agents/skill-registry.md` | Defines active repo skill root and legacy/tool-specific surfaces. | Yes. | Critical because `.codex/skills` in repo is legacy/custom. | `CORE_KEEP` | Keep. |
| `docs/agents/issue-tracker.md` | Adapts generic issue skills to Tenn GitHub issue rules. | Yes. | Overlaps AGENTS GitHub section. | `CORE_KEEP` | Keep as detailed reference. |
| `docs/agents/triage-labels.md` | Maps generic roles to Tenn labels. | Yes. | Prevents generic `triage` label drift. | `CORE_KEEP` | Keep. |
| `docs/agents/domain.md` | Tells generic skills which Tenn docs replace generic `CONTEXT.md`/ADR assumptions. | Yes. | Essential adapter for host skills. | `CORE_KEEP` | Keep. |
| `.claude/commands/*` | Tool-specific command prompts for Claude. | Mixed. | Duplicates host skills and Tenn repo policy. | `RENAME_OR_REHOME` | Keep as Claude-only reference, not Tenn canonical command list. |
| Host `~/.codex/rules/default.rules` | One prefix allow rule for an old news loader py_compile. | Low. | Too path-specific and stale as a general rule surface. | `DEPRECATE` | Do not copy into Tenn. |
| `.codex/skills/cockpit-flag-orchestrator` | Cockpit feedback artifact processor. | Yes for Cockpit. | Product/control-plane boundary, not general dev-flow. | `OWNER_BOUNDARY` | Leave out of reset. |

## Missing Or Stale Surfaces

- No nested `AGENTS.md` files were found. That is acceptable for now.
- No first-class repo `tenn-explain` skill exists.
- No first-class repo `tenn-review-board`, `tenn-fix`, `tenn-worker`, or
  `tenn-git-guard` skill exists.
- Generic `architecture-check` still references `.cursor/rules/*`; current repo
  evidence points agents to `docs/architecture/*` and `docs/agents/domain.md`.
  Treat direct `.cursor/rules` assumptions as stale unless live files prove
  otherwise.
