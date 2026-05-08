---
job_id: news_memo_env_gated_fallback_provenance_integration_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/news_memo_env_gated_fallback_provenance_integration_v1.md
  - docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md
  - scripts/backfill_missing_news_memos.py
  - scripts/load_news_to_qdrant.py
  - scripts/test_backfill_missing_news_memos.py
  - scripts/test_load_news_qdrant_preflight.py
  - financial-engine_v2/backend/app/services/news_memo_extractor.py
  - financial-engine_v2/backend/app/tasks/news_tasks.py
  - financial-engine_v2/backend/tests/test_news_memo_extractor.py
  - financial-engine_v2/backend/tests/test_news_tasks.py
  - financial-engine_v2/scripts/nightly_news.sh
  - reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/final_report.md
  - reports/agent_jobs/news_memo_env_gated_fallback_provenance_integration_v1/final_report.md
  - reports/agent_jobs/news_memo_env_gated_fallback_provenance_integration_v1/status.json
  - reports/agent_jobs/news_memo_env_gated_fallback_provenance_integration_v1/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_memo_env_gated_fallback_provenance_integration_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Safely integrate the isolated news memo env-gated fallback/provenance commit into the current preserve branch, preserving the ignored final report with explicit file allowlisting.

Primary lane:
Query Orchestration

Supporting lanes:
Provenance, Reporting, Evaluation

Mode:
SAFE EXTENSION / INTEGRATION

Source implementation:
- Worktree: /mnt/sdb2/home/l4nd0/tenn-news-memo-env-gated-fallback-provenance-v1
- Branch: codex/news-memo-env-gated-fallback-provenance-v1
- Commit: ebae61336f9a
- Commit subject: milestone(news): gate memo JSON fallback in ops
- Source final report:
  /mnt/sdb2/home/l4nd0/tenn-news-memo-env-gated-fallback-provenance-v1/reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/final_report.md

Goal:
Bring commit ebae61336f9a into the current preserve branch if collision checks are clean, and preserve the source final report as a tracked artifact without weakening task-card checks.

Required preflight:
1. Print branch and HEAD.
2. Run git status --short --untracked-files=all.
3. Run git worktree list.
4. Run git log --oneline -8.
5. Run registry/list-active if available.
6. Validate this task card.
7. Claim the task if safe.
8. Inspect source commit:
   git show --stat --oneline --name-status ebae61336f9a
9. Confirm source commit only touches allowed files.
10. Confirm source final report exists.
11. Check for dirty/untracked/deleted files overlapping the allowed files.

Hard stops:
- Stop if dirty/untracked/deleted files overlap this card’s allowed files.
- Stop if active registry jobs overlap this card’s files.
- Stop if ebae61336f9a touches files outside this card.
- Stop if cherry-pick conflicts.
- Stop if force-adding report files causes task-card check-diff failure.
- Do not touch production data, Qdrant, news DBs, company memory, market memory, financial truth, Cockpit frontend, or unrelated task cards.

Allowed work:
1. Cherry-pick ebae61336f9a into the current target branch if preflight is clean.
2. Copy and force-add the source final report exactly here:
   reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/final_report.md
3. Write the integration final report exactly here:
   reports/agent_jobs/news_memo_env_gated_fallback_provenance_integration_v1/final_report.md
4. If status.json or diff-check.json are generated and need tracking, use only the explicit allowed paths listed in this card.
5. If check-diff rejects any ignored report artifact despite exact allowlisting, leave the report on disk, do not commit it, and clearly report the blocker.

Validation after cherry-pick:
- Ruff on changed Python files.
- py_compile on changed scripts/modules.
- Focused pytest for changed news memo/backfill/task tests.
- Backfill CLI help probe.
- bash -n financial-engine_v2/scripts/nightly_news.sh.
- git diff --check.
- task-card check-diff.

Do not run:
- Live GPU fallback.
- Production news backfill.
- Qdrant rewrite/resync.
- Frontend repair action.
- Broad suite unless narrow tests expose a reason.

Definition of done:
- ebae61336f9a is integrated, or task stops with a clear collision report.
- Source final report is tracked, or preservation blocker is clearly reported.
- Validation results are recorded exactly.
- Registry claim is released.
- Final git status is reported.
- Integration report is written.

Final report must include:
- starting branch / HEAD
- final branch / HEAD
- source commit inspected
- source report preservation status
- registry status
- changed files
- tests/checks and exact results
- DATA_MISSING
- remaining risks
- whether live GPU fallback remains untested
- worktree status
- save recommendation
