---
job_id: remaining_task_cards_classification_audit_20260508
lane: Evaluation
owner: Claude
allowed_files:
  - docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md
  - reports/agent_jobs/remaining_task_cards_classification_audit_20260508/**
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/remaining_task_cards_classification_audit_20260508
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit and classify the remaining dirty task-card artifacts only. Produce a decision matrix and lane-separated preservation plan. Do not stage, commit, delete, revert, reset, clean, merge, or cherry-pick anything.

# Hard boundaries

- Do not edit source code.
- Do not stage files.
- Do not commit.
- Do not delete or revert the remaining task-card files.
- Do not modify the remaining task-card files except creating this new audit task card and writing this audit report.
- Do not touch scripts/news_pipeline/**.
- Do not touch financial-engine_v2/**.
- Do not touch cockpit-ui/**.
- Do not touch reports outside this job output directory.
- Do not touch other worktrees.
- Do not mutate Tenn databases, Qdrant, Postgres, SQLite stores, news stores, company memory, market memory, financial truth, gold/eval data, or runtime data.
- Allowed writes are only:
  - docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md
  - reports/agent_jobs/remaining_task_cards_classification_audit_20260508/**

# Required preflight

Run and record:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git rev-parse --abbrev-ref HEAD
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git log --oneline --decorate -10
- git status --short --untracked-files=all
- python3 scripts/agent_job_registry.py list-active || true
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md || true
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md || true

If graphify-out/GRAPH_REPORT.md exists, briefly inspect it before broader search:
- test -f graphify-out/GRAPH_REPORT.md && sed -n '1,120p' graphify-out/GRAPH_REPORT.md || true

# Scope

Classify only these existing dirty artifacts if present:

1. docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
2. docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
3. docs/agent_tasks/metric_extraction_current_state_audit_v1.md
4. docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md
5. docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md

Also classify the new audit task card you create, but do not include it in preservation recommendations except as this report’s own artifact.

# Audit questions for each task card

For each scoped artifact:

1. Existence and git state
   - exists / missing
   - modified tracked / untracked / clean / ignored
   - current size and modified timestamp
   - first 120 lines or enough content to classify

2. Contract validity
   - does it have valid YAML frontmatter?
   - can agent_job_contract validate it?
   - if invalid, what exact issue?
   - do not fix it

3. Job identity
   - job_id
   - lane
   - owner
   - mutation_mode
   - allowed_files
   - output_dir
   - production_data_access

4. Matching evidence
   - is there a matching reports/agent_jobs/<job_id>/ directory?
   - are report files ignored by git?
   - is there a matching branch/worktree?
   - is there a matching recent commit?
   - is there an active registry job for this job_id?
   - is there a stale registry job for this job_id?

5. Lane classification
   Use one primary lane:
   - Financial Truth
   - Evaluation
   - Provenance
   - Query Orchestration
   - Memory
   - Reporting

   Also tag if it touches:
   - News substrate / Ingestion
   - Cockpit UI
   - Runtime / Router
   - Metric Extraction
   - Repo Hygiene

6. Preservation value
   Classify:
   - HIGH: likely represents active/completed work that should not be lost
   - MEDIUM: useful context but needs report/branch validation
   - LOW: stale or duplicate but should be archived before deletion
   - UNKNOWN: DATA_MISSING

7. Cleanup recommendation
   Choose one:
   - preserve_later_in_lane_specific_commit
   - preserve_now_only_if_user_approves_mixed_docs_commit
   - archive_delete_later_after_report_review
   - revert_later_if confirmed accidental modification
   - leave_until_related_job_finishes
   - DATA_MISSING

   Explain why it should not be committed/deleted in this audit.

# Special checks

For the modified tracked file:
- git diff -- docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
- Determine whether the modification looks like:
  - accidental truncation
  - intentional update after newer runtime audit
  - formatting damage
  - duplicate/superseded content
  - DATA_MISSING

For each untracked task card:
- find matching report directory:
  - reports/agent_jobs/<job_id>/
- list files in matching report directory if present
- check whether matching report directory is ignored:
  - git check-ignore -v reports/agent_jobs/<job_id>/README.md || true
- search for matching branch/worktree names:
  - git branch --all --list '*<job_slug>*'
  - git worktree list --porcelain | grep -B2 -A3 '<job_slug>' || true
- search recent commits:
  - git log --all --oneline --decorate -- docs/agent_tasks/<filename> | head -20

# Required report artifacts

Write:

reports/agent_jobs/remaining_task_cards_classification_audit_20260508/README.md
reports/agent_jobs/remaining_task_cards_classification_audit_20260508/status.json
reports/agent_jobs/remaining_task_cards_classification_audit_20260508/task_card_matrix.md
reports/agent_jobs/remaining_task_cards_classification_audit_20260508/lane_separated_preservation_plan.md
reports/agent_jobs/remaining_task_cards_classification_audit_20260508/do_not_touch_yet.md

README.md must include:
- Executive summary
- Branch / HEAD
- Active registry status
- Current dirty status
- Classification table for each scoped artifact
- Highest-risk file
- Files recommended to preserve later
- Files recommended to archive/delete later
- Files that require user approval
- Files that should not be touched until another job finishes
- Whether a Project Memory save is recommended
- Final git status

status.json must include:
{
  "job_id": "remaining_task_cards_classification_audit_20260508",
  "mode": "audit_only",
  "primary_lane": "Evaluation",
  "started_head": "",
  "final_head": "",
  "scoped_files": [],
  "classified_files": [],
  "preserve_later": [],
  "archive_delete_later": [],
  "revert_later_candidates": [],
  "leave_until_related_job_finishes": [],
  "requires_user_approval": [],
  "matching_report_dirs": {},
  "matching_branches_or_worktrees": {},
  "active_registry_jobs": [],
  "cleanup_safe_now": false,
  "commit_safe_now": false,
  "project_memory_save_recommendation": "NO_SAVE|SAVE_RECOMMENDED|SAVE_REQUIRED",
  "collision_risk": "LOW|MEDIUM|HIGH",
  "data_missing": []
}

# Final response back to user

Report:
- branch / HEAD
- task card path
- report path
- whether any source code was touched
- current remaining dirty files
- classification summary by lane
- exact recommended next step
- whether commit/delete cleanup is safe now
- Project Memory save recommendation

Do not perform cleanup. Do not commit.
