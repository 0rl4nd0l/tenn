# Host Handoff Patch Proposal

Status: NOT_APPLIED

Target if owner explicitly approves host-global mutation in a future run:

```text
/home/l4nd0/.codex/skills/handoff/SKILL.md
```

Proposed addition:

```diff
@@
 Write a handoff document summarising the current conversation so a fresh agent can continue the work. Save to the temporary directory of the user's OS - not the current workspace.
+
+For Tenn repository work, prefer the repo-native `tenn-handoff` skill when it
+is available. It writes report-local `HANDOFF.md`, `NEXT_GOAL.md`, and ledger
+trace artifacts under `reports/agent_jobs/<job_id>/handoff/` and preserves
+task-card, git, validation, and owner-boundary state.
```

This host-global change was not applied in this run.
