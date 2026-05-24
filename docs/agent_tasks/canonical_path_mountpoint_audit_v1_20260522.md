---
job_id: canonical_path_mountpoint_audit_v1_20260522
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md
  - reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/
  - docs/
  - AGENTS.md
  - CLAUDE.md
  - .codex/
  - .claude/
  - scripts/agent_job_contract.py
  - scripts/agent_job_registry.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522
mutation_mode: safe_extension
production_data_access: false
---

# Canonical Path Mountpoint Audit

Audit and harden Tenn canonical repo/path/mountpoint guidance so Codex works only from the correct active location.

## Scope

- Primary lane: Evaluation
- Supporting lanes: Repo Hygiene, Reporting, Agent Control
- Mode: audit first; safe extension only if low risk
- Risk: medium; escalate to high and report-only if the safe fix would require symlink, mount, file move/delete, rsync, Docker/systemd, runtime/data/report binding, or old HDD preserve checkout changes.

## Required Preflight

- `pwd`
- `readlink -f /home/l4nd0/tenn`
- `readlink -f /home/l4nd0/tenn-runtime || true`
- `findmnt -T /home/l4nd0/tenn -o TARGET,SOURCE,FSTYPE,OPTIONS`
- `df -hT /home/l4nd0/tenn`
- `lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,ROTA`
- `git -C /home/l4nd0/tenn rev-parse --show-toplevel`
- `git -C /home/l4nd0/tenn branch --show-current`
- `git -C /home/l4nd0/tenn rev-parse HEAD`
- `git -C /home/l4nd0/tenn status --short --untracked-files=all`
- `git -C /home/l4nd0/tenn worktree list`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/canonical_path_mountpoint_audit_v1_20260522.md`
- Claim registry if safe.

## Audit Questions

1. What is the true canonical active repo entrypoint today?
2. What is the resolved real path?
3. What mount/device backs it?
4. Which paths are old HDD/preserve/archive/evidence-only?
5. Which paths are isolated safe/integrate worktrees and when should Codex use them?
6. Which paths appear in agent guidance, docs, scripts, task cards, reports, Makefiles, package scripts, or shell scripts?
7. Are any docs/prompts still telling agents to work from old HDD or ambiguous paths?
8. Are any registry roots or git common-dir paths pointing to unexpected HDD locations?
9. Are any runtime/data/report bindings still pointing to old paths?
10. Are there symlinks that are valid but confusing and need documentation?
11. What would be the safest one true path rule for future agents?
12. What should Codex do when launched from the wrong path?

## Allowed Fixes

- Add or update a small canonical-path section in agent guidance so agents default to `/home/l4nd0/tenn`.
- Add or update agent preflight instructions requiring symlink, branch, HEAD, status, worktree, and registry checks before mutation.
- Add a non-destructive helper script or doc snippet that prints canonical path diagnostics only if such a script location is already conventional.
- Warn that old HDD checkout paths are preserve/evidence-only.
- Warn that isolated worktrees are allowed for task execution, but final integration must target canonical `/home/l4nd0/tenn`.

## Forbidden Fixes

Do not delete, prune, move, rsync, remount, edit `/etc/fstab`, change systemd units, change Docker volumes, edit runtime/data/report bindings, alter Git remotes, clean untracked task cards, edit old HDD preserve checkouts, or change financial-engine runtime, DB, Qdrant, news, memory, parser, extraction, or Cockpit UI code.

## Output

Write the final report to `reports/agent_jobs/canonical_path_mountpoint_audit_v1_20260522/README.md`.
