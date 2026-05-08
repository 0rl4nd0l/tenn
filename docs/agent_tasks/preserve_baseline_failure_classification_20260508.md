---
job_id: preserve_baseline_failure_classification_20260508
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/preserve_baseline_failure_classification_20260508.md
  - reports/agent_jobs/preserve_baseline_failure_classification_20260508/
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/preserve_baseline_failure_classification_20260508
mutation_mode: audit_only
production_data_access: false
---

# Task

Classify the current preserve-branch baseline test failures after the news memo fallback/provenance landing. Do not fix code.

Primary lane:
Evaluation

Supporting lanes:
Architecture, Query Orchestration, Provenance, Memory, Reporting

Mode:
AUDIT ONLY

Goal:
Separate pre-existing/systemic baseline failures from the landed news memo work, assign each failure group to the correct lane/owner surface, and recommend the smallest safe next task cards.

Context:
News memo fallback/provenance has landed on preserve:
- Preserve branch: preserve/dirty-work-20260430T065748Z
- Milestone baseline commit: d2e648063287
- Integrated implementation commit: a3f3933
- Integration artifact commit: 3dda92a
- Focused news memo validation passed.
- Full Ruff passed.
- autodev/tests passed: 89 passed.
- scripts pytest baseline: 1 failed, 727 passed, 3 skipped.
- backend pytest baseline: 16 failed, 1503 passed, 1 deselected.

Known failure groups from last report:
1. scripts/test_probe_news_provider_coverage.py::ProbeProviderCoverageTests::test_probe_from_eodhd_capture
2. architecture invariant tests around sqlite/sqlite3 backend runtime usage
3. uuid/vector determinism tests around process_document/vector IDs
4. memo extractor signal-routing tests where BHP is dropped with candidates=[]
5. RAG payload guardrail/process_document tests
6. streaming subprocess tests where _run_action_subprocess_streaming() now requires keyword-only job_id
7. task-card check-diff blocked by unrelated dirty task-card drafts

Required preflight:
- branch
- HEAD
- git status --short --untracked-files=all
- git log --oneline -6
- git worktree list
- registry/list-active if available
- validate and claim task card if safe

Allowed work:
- Inspect failure logs, pytest output, relevant tests, and relevant source files.
- Re-run only the exact failing subset if needed.
- Write a report under reports/agent_jobs/preserve_baseline_failure_classification_20260508/.
- Do not edit implementation code.
- Do not edit tests.
- Do not stage unrelated dirty task-card drafts.

Do not touch:
- production data
- Qdrant
- news DBs
- company memory
- market memory
- financial truth
- Cockpit frontend
- implementation files
- existing dirty task-card drafts

Required output:
For each failure group, report:
- exact failing tests
- owning lane
- likely owner files
- Confirmed facts
- Inferred facts
- DATA_MISSING
- whether failure appears related to the news memo merge: YES / NO / UNCLEAR
- blast radius
- smallest safe next task
- whether it should be audit-only or safe-extension
- whether it is a blocker for current news memo milestone

Final report must include:
- branch / HEAD
- registry status
- exact commands run
- failure table
- lane ownership table
- recommended task-card queue
- repo hygiene notes for unrelated dirty task-card drafts
- save recommendation
