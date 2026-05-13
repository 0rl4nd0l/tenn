# Task Status Matrix

## Preflight task-card state

| command | result |
| --- | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | [Confirmed] `ok: true` |
| `python3 scripts/agent_job_registry.py list-active` | [Confirmed] `ok: true`, no active jobs |
| `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | [Confirmed] `ok: false`, blocked by four untracked task cards |
| `python3 scripts/agent_job_registry.py claim docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | [Confirmed] failed for same dirty files; no claim acquired |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | [Confirmed] `ok: false`, same disallowed files |

## Task-card inventory

[Confirmed] `find docs/agent_tasks -maxdepth 1 -type f` found 52 files. The following are the current focus set:

| task card | lane | owner | mutation_mode | report dir | current classification |
| --- | --- | --- | --- | --- | --- |
| `system_task_frontend_wiring_status_audit_v1_20260513.md` | Reporting | Codex | audit_only | `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513` | Current audit |
| `cockpit_upgrade_integration_readiness_20260509.md` | Reporting | Claude | audit_only | `reports/agent_jobs/cockpit_upgrade_integration_readiness_20260509` | Dirty untracked blocker |
| `eval_instrumentation_dirty_worktree_audit_20260509.md` | Evaluation | Claude | audit_only | `reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509` | Dirty untracked blocker |
| `news_memo_signal_routing_candidate_fixture_integration_v1.md` | Memory | Codex | safe_extension | `reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1` | Dirty untracked blocker, report blocked |
| `preserve_dirty_state_classification_20260512.md` | Reporting | Codex | audit_only | `reports/agent_jobs/preserve_dirty_state_classification_20260512` | Dirty untracked blocker |
| `cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md` | Reporting | Codex | safe_extension | Matching report dir | Recent integrated Cockpit Home work |
| `marketplace_recency_promote_to_target_v1.md` | Reporting | Codex | safe_extension | Matching report dir | Blocked/superseded risk |
| `metric_extraction_current_state_audit_v1.md` | Evaluation | Codex | audit_only | Matching report dir | Historical audit |
| `query_legacy_chat_merge_readiness_audit_v1.md` | Query Orchestration | Codex | audit_only | Matching report dir | Historical audit |
| `tenn_agent_mcp_v0_*` | Evaluation | Codex | mixed | Matching report dirs | Historical MCP work |

## Dirty work matrix

| path | git status | belongs to | blocks | treatment |
| --- | --- | --- | --- | --- |
| `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md` | `??` | Reporting/Claude | claim, check-overlap, check-diff | Preserve/commit/delete in dedicated hygiene task |
| `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md` | `??` | Evaluation/Claude | claim, check-overlap, check-diff | Preserve/commit/delete in dedicated hygiene task |
| `docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md` | `??` | Memory/Codex | claim, check-overlap, check-diff | Do not touch without Memory lane decision |
| `docs/agent_tasks/preserve_dirty_state_classification_20260512.md` | `??` | Reporting/Codex | claim, check-overlap, check-diff | Decide if it is current or superseded |
| `docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md` | `??` | Reporting/Codex | none for this task | Intentional audit artifact |

## Recent reports and stale evidence

| report dir | status evidence | freshness | notes |
| --- | --- | --- | --- |
| `cockpit_home_news_snapshot_c0549d7_source_integration_20260512` | status artifacts and recent commit | Fresh relative to HEAD history | Code still confirms Home BFF wiring |
| `preserve_dirty_state_classification_20260512` | report dir exists | Fresh but untracked task card | Likely related to current blockers |
| `news_memo_signal_routing_candidate_fixture_integration_v1` | status artifacts include blocked state | Current status DATA_MISSING until reviewed | Memory lane |
| `cockpit_upgrade_integration_readiness_20260509` | report dir exists | Stale or DATA_MISSING | Untracked task card |
| `eval_instrumentation_dirty_worktree_audit_20260509` | report dir exists | Stale or DATA_MISSING | Untracked task card |
| `repo_hygiene_classification_audit_20260508` | report dir exists | Stale but relevant history | Do not treat as current truth |
| `metric_extraction_current_state_audit_v1` | report dir exists | Stale | Useful only as historical evaluation context |

## Next-safe-step queue

| priority | step | classification |
| --- | --- | --- |
| 1 | Resolve the four pre-existing untracked task cards | Confirmed |
| 2 | Rerun `list-active`, `check-overlap`, `claim`, and `check-diff` | Confirmed |
| 3 | Run selected Cockpit route tests after claim succeeds | Inferred |
| 4 | Run route contract audit for rewrite-only vs BFF ownership | Inferred |
| 5 | Only then choose implementation work for Marketplace/Home/Memory | Inferred |

