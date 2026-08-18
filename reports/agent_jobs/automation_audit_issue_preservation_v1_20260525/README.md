# Automation Audit Issue Preservation

Job: `automation_audit_issue_preservation_v1_20260525`

Mode: `issue_logging_only` / `audit_preservation_only`

Primary lane: Reporting

Supporting lanes: Repo Hygiene, Ops, Evaluation

## Summary

This report preserves four automation-audit findings as GitHub issue drafts
without creating live issues. The audit found that Tenn's local automation is
partly working, but parts of the system are split across different schedulers,
worktrees, docs, and runtime ownership paths. Preserving these drafts keeps the
problems actionable before starting any new GitHub Issue System Protocol work.

## Current Repo Evidence

- Tenn repo path: `/home/l4nd0/tenn`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD at preflight: `80284a1560373de0302e5d4f2c4b87be705aa985`
- Status at preflight:
  - branch ahead of `origin/migration/clean-runtime-baseline-reconstruct-v1` by 13 commits
  - unrelated untracked task card: `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- Automation worktree: `/home/l4nd0/tenn-codex-automations-v1-20260516`
- Automation branch/HEAD: `safe/codex-automated-audit-runners-v1-20260516` / `31d5c80b8289de4baaf6546f42fdfe0aad23fa19`
- Tenn issue skills path: `/home/l4nd0/.codex/skills`
- Tenn issue skills git status: `DATA_MISSING`; `/home/l4nd0/.codex/skills` is not inside a git repository.

## Issue Drafts

Issue bodies are preserved in:

- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/issue_drafts.md`

Drafts preserved:

| Finding | Severity | Lane | Duplicate check | Issue created | Reason |
| ------- | -------- | ---- | --------------- | ------------- | ------ |
| Automation topology reconciliation | P1 | Reporting / Repo Hygiene | No matching GitHub issue or PR found by read-only search | NO | GitHub mutation not approved by task card |
| Registry read-only/no-lock list-active mode | P1 | Repo Hygiene | No matching GitHub issue or PR found by read-only search | NO | GitHub mutation not approved by task card |
| nightly_news.sh observability / systemd migration | P1 | Ops / Reporting | No matching GitHub issue or PR found by read-only search | NO | GitHub mutation not approved by task card |
| llama-server :8001 ownership/provenance audit | P1 | Ops / Evaluation | No matching GitHub issue or PR found by read-only search | NO | GitHub mutation not approved by task card |

## Duplicate Check

Read-only duplicate search evidence is preserved in:

- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/duplicate_check.md`

## Forbidden Mutation Attestation

- No product/backend/frontend/runtime code was changed.
- No DB/Qdrant/news/memory store was touched.
- No canonical financial truth was touched.
- No parser routing, extraction prompts, or gold labels were touched.
- No model/runtime/service config was touched.
- No GitHub issues, comments, labels, or closures were created.
- The unrelated untracked Tenn task card was not touched.

## Validation

- PASS: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- PASS: `python3 scripts/agent_job_registry.py list-active`
- FAIL: `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md --repo-root .`
  - active Reporting-lane job: `strategy_lab_readonly_subsystem_maturation_clean_worktree_integrate_v1_20260525`
  - unrelated dirty file outside allowlist: `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- PASS: `python3 -m json.tool reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/status.json`
- PASS: `git diff --check`
- FAIL: `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
  - unrelated dirty file outside allowlist: `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`

## DATA_MISSING

See:

- `reports/agent_jobs/automation_audit_issue_preservation_v1_20260525/data_missing.md`

## Next Safe Step

It is safe to start the GitHub Issue System Protocol task after this report is
validated, as long as the next task starts with a fresh task card that
explicitly authorizes GitHub issue creation and re-runs duplicate searches
immediately before mutation.
