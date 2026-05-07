---
job_id: marketplace_matches_workflow_audit_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/marketplace_matches_workflow_audit_v1.md
  - reports/agent_jobs/marketplace_matches_workflow_audit_v1/**
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/marketplace_matches_workflow_audit_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit the Cockpit Marketplace + Matches workflow end-to-end. Identify why few new matches are appearing, whether first-found timestamps already exist, and what minimal safe implementation path would add first-found visibility and recency sorting.

# Hard boundaries

No code changes outside the task card and report directory.
No database writes.
No live marketplace crawling unless a safe mocked/local harness already exists.
No financial truth, memory, RAG, Qdrant, Postgres, extraction, ASX, news, or main query-orchestrator changes.

# Validation

Run repo-state/preflight commands.
Inspect relevant code, routes, tests, schemas, fixtures, reports, and docs.
Run read-only tests or static checks only if safe and already available.
Do not "fix" failing tests unless a separate implementation task is approved.

# Final report

Write:
reports/agent_jobs/marketplace_matches_workflow_audit_v1/README.md

Include Confirmed / Inferred / Speculative / DATA_MISSING sections, exact files inspected, commands run, and next safe implementation plan.
