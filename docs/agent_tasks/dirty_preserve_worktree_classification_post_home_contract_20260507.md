---
job_id: dirty_preserve_worktree_classification_post_home_contract_20260507
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md
  - reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/**
approval_required: false
timeout_seconds: 1200
output_dir: reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify remaining dirty/untracked preserve-worktree artifacts after the Cockpit Home contract scaffold commit.

Primary lane: Evaluation
Supporting lanes: Reporting, Provenance

# Context

Cockpit Home contract scaffold landed at:

- `47cb4c510cf5 feat(reporting): add cockpit home contract scaffold`

That milestone committed only:

- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/types/cockpit-home.ts`
- `docs/agent_tasks/cockpit_home_contract_design_v1.md`
- `reports/agent_jobs/cockpit_home_contract_design_v1/README.md`
- `reports/agent_jobs/cockpit_home_contract_design_v1/diff-check.json`

Remaining dirty/untracked preserve-worktree artifacts must now be classified before further Cockpit Home BFF implementation.

# Allowed writes

Only:

- this task card
- report artifacts under `reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/`

# Forbidden work

Do not:

- edit runtime code
- stage files
- commit files
- delete files
- move files
- archive files
- clean ignored/untracked artifacts
- mutate data stores
- run ingestion/reindex/resync
- implement Cockpit Home BFF route
- change backend, frontend, chat, query orchestrator, source labels, or memory behavior

# Required preflight

Run and report:

- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short --untracked-files=all`
- `git status --ignored --short`
- `git worktree list`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /mnt/sdb2/home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/dirty_preserve_worktree_classification_post_home_contract_20260507.md --repo-root /mnt/sdb2/home/l4nd0/tenn`

Claim only if safe and repo rules support it.

# Classification required

Classify every dirty/untracked/ignored artifact into one of:

- keep_and_commit_now
- keep_but_commit_later
- archive_only
- delete_candidate_needs_user_approval
- move_to_separate_lane
- already_superseded
- DATA_MISSING

For each file or directory, report:

- path
- tracked/untracked/ignored status
- likely lane
- likely source/job
- whether it overlaps Cockpit Home future work
- recommended treatment
- whether user approval is required
- exact safe next command, if any, but do not run it

Pay special attention to:

- `docs/agent_tasks/*`
- `reports/agent_jobs/*`
- `tenn_cockpit_home_design_export_20260506/`
- `tenn_prompt_contracts_response_guidelines.zip`
- any source-ref or design-export files
- any leftover Cockpit Home audit/report artifacts
- any source-label/chat/verification task cards

# Required output

Write:

`reports/agent_jobs/dirty_preserve_worktree_classification_post_home_contract_20260507/README.md`

Include:

1. Branch / HEAD / worktree / registry status
2. Current dirty/untracked/ignored inventory
3. Classification table
4. Recommended keep/commit set
5. Recommended archive/delete candidates, with user approval required
6. Files that should move to separate lane/task
7. Files that may block Cockpit Home BFF route v1
8. Exact suggested next commands, grouped by option, but do not run them
9. Collision risk
10. DATA_MISSING
11. Whether Cockpit Home BFF route v1 can safely start now or should wait
12. Project Memory save recommendation

After the task card is created/validated:

1. Run the preflight.
2. If safe, claim the audit.
3. Perform classification only.
4. Write the report.
5. Run `git diff --check`.
6. Run task-card `check-diff`.
7. Release claim if supported.
8. Final response must include exact files written and final repo status.

Hard stop:
If classification requires modifying/deleting/staging/committing files, do not do it. Report only.
