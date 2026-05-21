---
job_id: sloppy_fix_manual_only_pr_landing_v1
lane: Evaluation
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/sloppy_fix_manual_only_v1.md
  - docs/agent_tasks/sloppy_fix_manual_only_pr_landing_v1.md
  - reports/agent_jobs/sloppy_fix_manual_only_pr_landing_v1/**
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/sloppy_fix_manual_only_pr_landing_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create a clean PR branch from origin/main that contains only the Sloppy Fix manual-only mitigation and the relevant task-card artifacts, then open a PR to main.

# Hard boundaries

Do not push the existing `safe/sloppy-fix-manual-only-v1-20260521` branch.
Do not direct-push to `main`.
Do not merge, approve, or auto-merge the PR.
Do not enable, disable, rerun, cancel, delete, or edit remote GitHub Actions.
Do not modify Sloppy Scan, Claude, CodeQL, Dependabot, `.sloppy.yml`, local `tenn-codex-*` timers, systemd units, Codex automations, runtime services, DBs, Qdrant, memory stores, parser routing, extraction prompts, migrations, ingestion, sync, backfills, or production data.
Do not broaden into action pinning, permission reduction, provider/model changes, or secret handling.
Do not use Chrome/browser automation.

# Required preflight

1. cd /home/l4nd0/tenn-sloppy-fix-manual-only-v1-20260521
2. Print current worktree path.
3. Print branch and HEAD.
4. Run `git status --short --untracked-files=all`.
5. Run `git worktree list`.
6. Validate `docs/agent_tasks/sloppy_fix_manual_only_v1.md`.
7. Run registry/list-active if available.
8. Run registry/check-overlap for the PR landing task if available.
9. Claim this task if registry supports it and overlap is clean.
10. Verify GitHub CLI auth and git push auth. If auth is broken, stop and report exact fix needed; do not improvise credentials.

# Implementation

Create a fresh worktree/branch from origin/main:

```bash
git fetch origin main
git worktree add -b safe/sloppy-fix-manual-only-main-pr-v1-20260521 /home/l4nd0/tenn-sloppy-fix-manual-only-main-pr-v1-20260521 origin/main
cd /home/l4nd0/tenn-sloppy-fix-manual-only-main-pr-v1-20260521
```

Cherry-pick only the known good commit:

```bash
git cherry-pick 4a6164237638b8876cfee1ad7570359b9a6b74b0
```

If cherry-pick conflicts, stop and report. Do not resolve broad conflicts without approval.

Create or copy the PR landing task card:

```text
docs/agent_tasks/sloppy_fix_manual_only_pr_landing_v1.md
```

Do not include unrelated task cards or reports in the commit unless the repo contract requires the PR landing task card to be committed. If adding the PR landing task card creates a second commit, make that commit contain only the PR landing task card.

# Validation before push

Run:

```bash
rg -n "workflow_dispatch" .github/workflows/sloppy-fix.yml
if rg -n "schedule:|cron:" .github/workflows/sloppy-fix.yml; then exit 1; fi
git diff --check
git show --name-status --oneline --no-renames HEAD
git status --short --untracked-files=all
```

Confirm the Sloppy Fix mitigation commit changes exactly:

```text
.github/workflows/sloppy-fix.yml
docs/agent_tasks/sloppy_fix_manual_only_v1.md
```

If the PR landing task card is committed, confirm it is the only additional committed file.

Do not push if any unexpected files appear.

# Push and PR

After validation passes, push only the fresh PR branch:

```bash
git push -u origin safe/sloppy-fix-manual-only-main-pr-v1-20260521
```

Create a PR:

```bash
gh pr create \
  --base main \
  --head safe/sloppy-fix-manual-only-main-pr-v1-20260521 \
  --title "Make Sloppy Fix manual-only" \
  --body "Removes the scheduled cron trigger from Sloppy Fix while preserving workflow_dispatch. No workflow settings were changed remotely. This PR is limited to the workflow mitigation and task-card artifact."
```

Do not merge the PR.

# Required report

Write:

```text
reports/agent_jobs/sloppy_fix_manual_only_pr_landing_v1/README.md
reports/agent_jobs/sloppy_fix_manual_only_pr_landing_v1/status.json
```

README.md must include:

TENN SLOPPY FIX MANUAL-ONLY PR LANDING
Starting branch / HEAD / worktree
New PR branch / HEAD / worktree
Registry / lock status
Preflight summary
Cherry-pick result
Exact committed files
Validation results
Push result
PR URL
Confirmation PR was not merged
Confirmation no remote GitHub Actions settings were changed
DATA_MISSING
Final git status
Project Memory save recommendation

status.json must include:

```json
{
  "job_id": "sloppy_fix_manual_only_pr_landing_v1",
  "status": "GREEN_OR_YELLOW_OR_RED",
  "source_commit": "4a6164237638b8876cfee1ad7570359b9a6b74b0",
  "pr_branch": "safe/sloppy-fix-manual-only-main-pr-v1-20260521",
  "pushed": false,
  "pr_created": false,
  "pr_url": "",
  "workflow_dispatch_present": null,
  "schedule_present": null,
  "cron_present": null,
  "unexpected_files": [],
  "remote_actions_settings_modified": false,
  "pr_merged": false,
  "data_missing": [],
  "user_approval_needed": false,
  "gpt_review_recommended": true
}
```

Status rules:

GREEN: fresh PR branch pushed, PR opened, exact scoped diff verified, no schedule/cron remains in branch, workflow_dispatch remains, no PR merge.
YELLOW: local PR branch prepared but push or PR creation blocked by auth.
RED: cherry-pick conflict, unexpected files, schedule/cron remains, workflow_dispatch missing, direct push to main, existing wide branch pushed, or remote Actions settings changed.

Definition of done:

Fresh branch from origin/main created.
Only the approved mitigation is cherry-picked.
Scoped validation passes.
Fresh branch pushed.
PR to main opened.
PR not merged.
Registry claim released if one was created.
