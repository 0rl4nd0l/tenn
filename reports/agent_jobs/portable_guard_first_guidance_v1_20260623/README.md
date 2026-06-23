# Portable Guard First Guidance Report

## Summary

Status: DONE.

This docs-only control-plane task makes the portable repo-backed
`tenn-git-guard` runner the first-class preflight command in active operator
guidance.

## Scope

- Started from canonical
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `1a0f1a03741d692089a0125ecb2f10691b8da597`.
- Changed active operator guidance and repo-backed skill wording only.
- Did not inspect or mutate the protected BFF worktree beyond unavoidable
  registered-worktree names emitted by read-only guard preflight.
- Did not touch product, runtime, data, extraction, count-24, Greyhound runtime,
  or host-global files.

## Before

Several active guidance surfaces still led with repo-local
`scripts/agent_job_registry.py`, `scripts/agent_task_ledger.py`, or
`scripts/agent_job_contract.py` commands. That made runtime/product repos look
broken when they simply did not vendor Tenn control-plane scripts.

## After

Active guidance now says to run the portable guard first:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

From a Tenn control-plane checkout, the repo-backed fallback is:

```bash
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json
```

Repo-local `scripts/agent_*` commands are now described as
Tenn-control-plane-local checks or fallback validation.

## Runtime Functionality Proof

Not applicable. This task is docs-only and control-plane-only. No runtime,
product, data, extraction, automation, or Greyhound functionality was changed or
claimed.

## Collision Check

Portable guard preflight reported a separate
`control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623` registry
record with broad docs allowlists. The recorded PID was not alive during the
read-only collision check, no matching open PR existed, and no matching remote
branch existed. The stale registry record was not cleaned or mutated.
