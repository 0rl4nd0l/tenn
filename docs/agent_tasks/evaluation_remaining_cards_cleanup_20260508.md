---
job_id: evaluation_remaining_cards_cleanup_20260508
lane: Evaluation
owner: Claude
allowed_files:
  - docs/agent_tasks/evaluation_remaining_cards_cleanup_20260508.md
  - docs/agent_tasks/preserve_baseline_failure_classification_20260508.md
  - docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md
  - reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/**
  - reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/README.md
  - reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/status.json
  - reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1500
output_dir: reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508
mutation_mode: safe_extension
production_data_access: false
---

# Task

Classify and safely resolve only the two remaining Evaluation dirty task-card artifacts. Produce a clean preservation/hold result. Do not touch any source or runtime files.

# Hard boundaries

- Do not touch financial-engine_v2/**.
- Do not touch cockpit-ui/**.
- Do not touch scripts/news_pipeline/**.
- Do not touch Tenn databases, Qdrant, Postgres, SQLite stores, news stores, company memory, market memory, financial truth, gold/eval data, or runtime data.
- Do not clean, prune, delete worktrees, reset unrelated files, stash, rebase, merge, or cherry-pick.
- Do not touch Reporting/Cockpit artifacts already preserved or restored.
- Do not stage reports outside reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/.
- If either card is not Evaluation-lane or evidence is unclear, stop and report instead of guessing.

# Required preflight

Run and record:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git rev-parse --abbrev-ref HEAD
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git log --oneline --decorate -8
- git status --short --untracked-files=all
- python3 scripts/agent_job_registry.py list-active || true
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/evaluation_remaining_cards_cleanup_20260508.md || true
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/evaluation_remaining_cards_cleanup_20260508.md || true

# Required evidence checks

For each dirty file:

1. docs/agent_tasks/preserve_baseline_failure_classification_20260508.md
2. docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md

Run:

- test -f <file> && stat -c '%n %s %y' <file>
- sed -n '1,220p' <file>
- python3 scripts/agent_job_contract.py validate <file> || true
- git log --all --oneline --decorate -20 -- <file>
- extract job_id / lane / owner / mutation_mode / output_dir from YAML
- test for matching report dir: reports/agent_jobs/<job_id>/
- if matching report dir exists: ls -la reports/agent_jobs/<job_id> && find reports/agent_jobs/<job_id> -maxdepth 1 -type f -printf '%f %s bytes\n'
- git check-ignore -v reports/agent_jobs/<job_id>/README.md || true
- git branch --all --list '*<job_slug>*'
- git worktree list | grep -i '<job_slug>' || true
- python3 scripts/agent_job_registry.py check-overlap <file> || true

# Classification rules

Classify each file as one of:

- preserve_now
- preserve_later
- hold_until_related_job_finishes
- wrong_lane_do_not_touch
- archive_delete_later_after_user_approval
- DATA_MISSING

For each, include:
- primary lane
- supporting lanes
- whether it has a matching report bundle
- whether it has branch/worktree evidence
- whether it appears to record a blocker or completed job
- whether it should be committed now
- why/why not

# Expected handling guidance

1. `preserve_baseline_failure_classification_20260508.md`
   - Preserve now only if it is a valid Evaluation task card or blocker record and not tied to unverified/live source changes.
   - If it appears to be a future task or unrelated lane, leave unstaged and report.

2. `reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
   - Preserve now only if it is an Evaluation blocker/coordination record that should remain visible for future cleanup.
   - If it depends on unfinished Cockpit Home News Snapshot integration, preserve as a blocker record only if the evidence supports it.
   - Otherwise hold and report.

# Report

Create:

reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/README.md
reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/status.json

README.md must include:
- Executive summary
- Branch / starting HEAD
- Active registry status
- Classification of each dirty file
- Files preserved
- Files explicitly left unstaged
- Files held for later
- Staged diff check
- Commit SHA if successful
- Remaining dirty files
- Whether main worktree is now clean or still dirty
- Next recommended action
- Project Memory save recommendation

status.json must include:
{
  "job_id": "evaluation_remaining_cards_cleanup_20260508",
  "mode": "safe_extension",
  "primary_lane": "Evaluation",
  "started_head": "",
  "final_head": "",
  "classified_files": [],
  "preserved_files": [],
  "explicitly_not_staged": [],
  "held_for_later": [],
  "commit": null,
  "cleanup_performed": false,
  "source_code_touched": false,
  "validation": [],
  "remaining_dirty_files": [],
  "worktree_clean_after": false,
  "collision_risk": "LOW|MEDIUM|HIGH",
  "data_missing": []
}

# Staging rules

Always stage:
- docs/agent_tasks/evaluation_remaining_cards_cleanup_20260508.md
- reports/agent_jobs/evaluation_remaining_cards_cleanup_20260508/

Stage conditionally:
- docs/agent_tasks/preserve_baseline_failure_classification_20260508.md only if classified preserve_now.
- docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md only if classified preserve_now.

Use git add -f for report bundle if reports/ is ignored.

Before commit:

- git diff --cached --name-status
- git diff --cached --stat
- git status --short --untracked-files=all
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/evaluation_remaining_cards_cleanup_20260508.md || true

Hard stop if staged files include anything outside allowed_files.

# Commit

If staged files are exactly within allowed_files and evidence supports preservation, commit with:

git commit -m "docs(evaluation): preserve remaining hygiene task-card state"

After commit:

- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
