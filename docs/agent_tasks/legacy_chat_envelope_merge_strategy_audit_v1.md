---
job_id: legacy_chat_envelope_merge_strategy_audit_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md
  - reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/**
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit whether/how to merge `integrate/query-legacy-chat-envelope-compat-v1` at `bcdb57dc9aa3` into the preserve branch/worktree without mixing unrelated dirty work.

# Hard boundaries

Do not merge, cherry-pick, rebase, stage, commit, edit code, edit tests, edit Cockpit UI, mutate databases, touch Qdrant, run ingestion, modify financial truth, modify memory DBs, or change source-drawer UI.

Allowed writes are only this task card and the report files under `reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/`.

# Required preflight

Report:
- current repo path
- branch
- HEAD
- `git status --short --untracked-files=all`
- `git worktree list`
- recent commits relevant to preserve and the integration branch
- whether `bcdb57dc9aa3`, `ad1caa2`, and/or `9fc3d158f0ca` are contained in preserve HEAD
- active task card status
- registry/list-active status if supported
- dirty/untracked/deleted files by lane
- overlap between dirty files and the integration branch touched files

# Inspection targets

Read-only inspect:
- `CLAUDE.md`
- `AGENTS.md` if present
- `docs/claude/STATE.md` if present
- task-card/registry docs if present
- `docs/agent_tasks/query_legacy_chat_envelope_integration_v1.md`
- `reports/agent_jobs/query_legacy_chat_envelope_integration_v1/README.md`
- `reports/agent_jobs/query_legacy_chat_envelope_integration_v1/diff-check.json`
- `reports/agent_jobs/query_legacy_chat_envelope_integration_v1/status.json`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/tests/test_chat_route.py`

# Required analysis

Determine:
1. Whether clean integration branch `integrate/query-legacy-chat-envelope-compat-v1` exists locally.
2. Whether preserve already contains `bcdb57dc9aa3`, `ad1caa2`, or equivalent changes.
3. Whether a merge/cherry-pick would conflict mechanically.
4. Whether dirty preserve worktree files overlap the integration touched files.
5. Whether unrelated dirty Cockpit UI/design/export/task-card files would be at risk.
6. Whether report artifacts are tracked, ignored, or require force-add in a future integration job.
7. Whether the safest next action is:
   - no-op because already integrated,
   - clean merge from the integration branch,
   - cherry-pick code commit only,
   - cherry-pick code + report commit,
   - create another fresh integration worktree,
   - stop because collision risk remains HIGH.

# Validation

Audit-only validation:
- `git diff --check` only if it does not require staging or mutation.
- Use read-only `git merge-tree`, `git log --contains`, `git branch --contains`, `git diff --name-only`, or equivalent safe commands.
- Do not run broad test suites unless they are strictly read-only and already supported by the current repo state.
- Do not attempt to fix the `app.models.companies` collection blocker.

# Final report

Write:
`reports/agent_jobs/legacy_chat_envelope_merge_strategy_audit_v1/README.md`

Include:
- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- branch / HEAD / worktree / status evidence
- task-card status
- registry status
- exact files inspected
- exact commands run
- dirty/untracked/deleted files classified by lane
- containment status for `bcdb57dc9aa3`, `ad1caa2`, and `9fc3d158f0ca`
- overlap assessment
- collision risk: LOW / MEDIUM / HIGH
- recommended next safe step
- whether a follow-up safe-extension task card is needed
- whether Project Memory save is recommended
