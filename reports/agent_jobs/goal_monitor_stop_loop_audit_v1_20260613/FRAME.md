# Frame

## Objective
Audit and repair Tenn goal-monitor / stop-state behavior so completed handoffs do not keep looping.

## Why This Matters
Repeated post-handoff Stop-hook output burns tokens and weakens terminal-state discipline.

## Non-Negotiables
- Control-plane only.
- Do not touch product, runtime, data, extraction, count-24, GitHub, DB, Qdrant, news, memory, services, prompts, model/GPU config, branches, or worktrees.
- Preserve unrelated untracked `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`.

## Judgement Rules
- Treat current repo and host hook evidence as authoritative.
- Mark missing post-handoff transcript evidence as `DATA_MISSING`.
- Implement only a minimal hook behavior change if it is task-card allowlisted and focused.

## Scope In
- Repo AGENTS, Tenn skills, task-card/registry/hook scripts, `.codex` hook config, host-local goal optimizer surfaces, `/tmp` handoff, report-local artifacts.

## Scope Out
- Product/runtime/extraction/data/greyhound prediction work and all destructive or GitHub operations.

## Evidence Sources
- Live branch `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609`, HEAD `9dfa0f83cc09bf2e9edf40f659e0e2fdce0fa374`.
- `AGENTS.md`, `.agents/skills/*`, `.codex/hooks.json`, `scripts/agent_job_hook.py`, host `~/.codex/hooks/stop_check.py`, host goal optimizer scripts.
- `/tmp/greyhound_accuracy_odds_closeout_20260613T0854.md`.

## Success Shape
- Required report bundle exists.
- The goal/stop surfaces are explained.
- A minimal repo-side Stop-hook fix is implemented and validated with focused checks.

## Stop States
- `WAITING_ON_USER` if host-global hook mutation is required.
- `DONE_WITH_RISK` if repo-side fix lands but pytest is unavailable or host-global hook still needs a separate approved patch.
- `DONE` only if all focused validation and guard checks pass with no residual blocker.

## Steering Log
- 2026-06-13 20:00 Australia/Melbourne - User required Tenn control-plane-only audit and repair, no count-24 touch, no product/runtime/data/extraction/greyhound work.
