# Fix Plan

## Implemented In This Task

Change repo-local `scripts/agent_job_hook.py` so a successful Codex `Stop` event returns `{}` instead of a pass `systemMessage`.

This keeps Stop silent when the task-card contract passes. Real failures still return `decision: block`.

## Why This Is Minimal

- It touches only the repo hook and focused hook tests.
- It does not change registry, task-card, product, runtime, extraction, data, GitHub, DB, Qdrant, news, memory, service, prompt, model/GPU, branch, or worktree state.
- It preserves non-Stop pass context for Codex `BeforeTool` and existing non-Codex integrations.

## Host-Global Follow-Up Prompt

Use this as the next bounded prompt if host-global hook mutation is approved:

```text
Patch `/home/l4nd0/.codex/hooks/stop_check.py` only. Do not touch Tenn product/runtime/data/extraction files. Make the Stop hook warning-only and loop-resistant:

1. Resolve the repo from hook payload cwd or current cwd instead of hard-coded `/home/l4nd0/tenn`.
2. Emit no message when the only change is a pre-existing unrelated dirty file already reported in the same thread/repo fingerprint.
3. Persist a small dedupe fingerprint under `/tmp/codex-stop-check/` keyed by thread id, cwd, changed-file set, and message class.
4. If a handoff-complete marker or configured handoff path is present, suppress informational dirty warnings and return `{}`.
5. For dirty warnings that still emit, state clearly: "Informational only; do not continue work unless the user asked for cleanup or commit."
6. Add a synthetic self-check for unchanged repeated dirty state returning `{}` on the second Stop.
```

## Optional Repo Follow-Up

Add an explicit Tenn skill rule: after a report/handoff reaches `DONE`, `DONE_WITH_RISK`, or `WAITING_ON_USER`, the next assistant message should be final only; agents should not answer repeated informational Stop-hook warnings with new work.
