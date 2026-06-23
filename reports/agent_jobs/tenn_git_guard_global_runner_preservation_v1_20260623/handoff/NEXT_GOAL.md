# Next Goal

Work in:
`/home/l4nd0/tenn-control-plane-task-ledger-status-refresh-v1-20260623`

Read first:
`reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/HANDOFF.md`

Then run the repo-backed guard:

```bash
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "tenn git guard global runner preservation" --json
```

Act as a bounded orchestrator. Preserve the `tenn-git-guard` runner lane
separately from runtime/product work. Verify the preservation branch state before
any merge or cleanup decision. Do not mutate registry, clean owner-boundary
files, or touch product/runtime/data/extraction paths unless explicitly
approved.

Stop with Greyhound promotion still blocked unless a later completed full daemon
child proves 100+ safe eligible races and all gate contracts pass.
