---
job_id: query_legacy_chat_merge_readiness_audit_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/query_legacy_chat_merge_readiness_audit_v1.md
  - reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit merge readiness for the isolated legacy /chat evidence-envelope compatibility patch.

# Required preflight

Run and report:
- pwd
- branch
- HEAD
- git status --short --untracked-files=all
- git worktree list
- recent commits
- active task card
- task-card validation
- registry/list-active if available
- registry/check-overlap if available
- registry claim if safe

Then inspect, without modifying, both:
- preserve worktree: /mnt/sdb2/home/l4nd0/tenn
- patch worktree: /mnt/sdb2/home/l4nd0/tenn-legacy-chat-envelope-compat-v1

# Audit questions

1. What is the current HEAD of the preserve worktree?
2. What is the current HEAD of the patch worktree?
3. What is the ancestry relationship among:
   - c68abe138eb4
   - 9defaed58dc0
   - 9fc3d158f0ca
   - current preserve HEAD
4. Is 9fc3d158f0ca already contained in preserve HEAD?
5. Is 9defaed58dc0 already contained in preserve HEAD?
6. Which files would be touched if integrating 9fc3d158f0ca?
7. Do any of those files overlap dirty/untracked files in the preserve worktree?
8. Are any dirty preserve-worktree files in Query Orchestration, Provenance, Reporting, backend API, or backend tests?
9. Would cherry-picking only 9fc3d158f0ca onto preserve be clean, conflicted, or semantically unsafe?
10. Would preserving the audit commit 9defaed58dc0 separately be useful, required, or unnecessary?
11. What exact integration path is safest:
    - no integration yet
    - cherry-pick only 9fc3d158f0ca later
    - cherry-pick 9defaed58dc0 then 9fc3d158f0ca later
    - merge branch later
    - create a fresh clean integration branch from preserve HEAD
    - block until dirty Cockpit UI/design work is committed/stashed/archived
12. What exact validation should run after integration?
13. Is /save recommended after this audit?

# Hard stops

Stop and report only if:
- task card invalid
- registry overlap is active and relevant
- audit would require editing code
- production data access would be needed
- dirty preserve files overlap the patch surfaces in a way that makes conclusions unreliable
- the patch worktree is no longer clean
- ancestry cannot be determined safely

# Allowed writes

Only write:
- docs/agent_tasks/query_legacy_chat_merge_readiness_audit_v1.md
- reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md
- optional JSON/markdown support files under reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/

Do not edit, cherry-pick, merge, stash, reset, commit, or delete anything.
Do not modify either worktree except for the allowed task card/report artifacts in the audit worktree.

# Do not touch

- cockpit-ui/**
- Cockpit Home files
- marketplace/watchlist/news/settings/verification UI files
- ingestion
- Qdrant
- news.sqlite
- memory DBs
- financial truth / extraction
- deep research
- source drawer UI
- retrieval ranking
- dirty preserve-worktree files

# Required output

Final report must include:
- Confirmed facts
- Inferred facts
- Speculative claims
- DATA_MISSING
- worktrees inspected
- preserve HEAD/status
- patch HEAD/status
- ancestry graph or concise ancestry summary
- files in 9fc3d158f0ca
- preserve dirty-file overlap analysis
- integration risk: LOW / MEDIUM / HIGH
- safest integration recommendation
- exact commands the user should run later if safe, but do not run them
- exact tests/checks to run after integration
- whether report artifacts are ignored by git and need force-add
- final git status
- registry release status
- /save recommendation
