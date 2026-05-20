# Post-NVMe Memory/A2M Audit Artifact Checkpoint

Job ID: `post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519`

## Confirmed Facts

- Runtime worktree: `/home/l4nd0/tenn-runtime`, resolving to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch at preflight: `migration/clean-runtime-baseline-reconstruct-v1`.
- Preflight HEAD: `0b8c4d942be5` (`fix(query): allow cockpit control prompts without source refusal`).
- Recent baseline already preserved in `2e73de32ac77` (`milestone(evaluation): checkpoint nvme runtime audit artifacts`).
- Registry preflight reported `active_jobs: []`.
- Registry claim succeeded for this checkpoint job.
- Artifact copy did not rerun DB, Qdrant, runtime, APEX, Home, extraction, or news validation.
- Artifact copy included task-card/report files only. No source code, runtime config, scripts, DB files, Qdrant stores, news stores, memory stores, model files, parser/extraction code, or Cockpit UI/source files were copied.
- Secret scan over the preserved task cards and report directories found only plain-language references to secret-handling boundaries, not credential-shaped values.

## DATA_MISSING

- This checkpoint did not independently rerun the underlying audits.
- This checkpoint did not make live DB, Qdrant, runtime, APEX, Home, extraction, news, or memory-store calls.
- The final commit hash for this exact checkpoint commit is not knowable inside this README before the README is committed. The post-commit closeout records the final hash.
- The final post-release registry status is recorded in `status.json` after registry release.

## Preserved Artifacts

Task cards:

- `docs/agent_tasks/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519.md`
- `docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md`
- `docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md`
- `docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md`
- `docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md`
- `docs/agent_tasks/memory_contamination_live_inventory_readonly_v1_20260519.md`
- `docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md`

Report directories:

- `reports/agent_jobs/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519/`
- `reports/agent_jobs/cockpit_chat_orchestration_side_effect_audit_v1_20260519/`
- `reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/`
- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/`
- `reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/`
- `reports/agent_jobs/memory_contamination_live_inventory_readonly_v1_20260519/`
- `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/`

## Source Worktrees

- Checkpoint task card/report: `/home/l4nd0/tenn-runtime`.
- Cockpit chat orchestration side-effect audit: `/home/l4nd0/tenn-runtime`.
- Cockpit control-prompt guard tests report: `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`.
- Cockpit control-prompt guard tests task card: copied from `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`; it differed from the active runtime copy only by the worktree path line.
- Gold Metric Coverage Audit v1: `/home/l4nd0/tenn-runtime`.
- Memory Contamination Root Cause Audit: `/home/l4nd0/tenn-memory-contamination-root-cause-audit-v1-20260519`.
- Memory live inventory read-only: `/home/l4nd0/tenn-memory-live-inventory-readonly-v1-20260519`.
- A2M News Trace / Entity-Linking Blast-Radius Audit: `/home/l4nd0/tenn-a2m-news-trace-audit-v1-20260519`.

## Force-Add Status

- `reports/` is ignored in this repository, so preserved report directories require `git add -f`.
- The task cards under `docs/agent_tasks/` do not require force-add.

## Registry Status

- Claim: `ok=true`.
- Claim was refreshed after exact report child paths were added to the task card.
- Claimed job: `post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519`.
- Release: `ok=true`; active registry record removed by `scripts/agent_job_registry.py release`.

## Audit Result Summaries

Cockpit chat orchestration side-effect audit:

- Direct APEX/M40 serving remains the stable baseline for tiny direct local prompts.
- The observed behavior belongs to Cockpit route orchestration: prompt wrapping, visible-source enforcement, response delivery metadata, persistence, and auto-diagnostic flagging.
- `Reply exactly: ok` can be replaced by route-level `missing_visible_sources`; the larger follow-up request seen in logs is consistent with auto-diagnostic bundle analysis.
- DATA_MISSING: no fresh `/api/cockpit/chat` route smoke was run because it would persist chat and diagnostic artifacts.

Cockpit control-prompt guard tests and isolated implementation report:

- Tests-first isolated work proved a narrow source-free literal control-prompt exemption.
- The route can deliver `ok` for `Reply exactly: ok` without `missing_visible_sources` replacement.
- Guard-only literal control prompts do not create auto-diagnostic findings by themselves.
- Substantive source-free requests still hit the visible-source refusal path.

Gold Metric Coverage Audit v1:

- `canonical_core`: `10` documents and `24` checks; strict no-regression anchor only.
- `expanded_required`: `15` documents and `39` checks; current required-subset stability only.
- `confirmed_metric_coverage`: `15` fixtures and `146` expectations; breadth inventory/readiness, not a fresh extracted-payload scoring run.
- Broad production extraction coverage claims are not supported by the current artifacts.

Memory Contamination Root Cause Audit:

- `ROOT_CAUSE_CONFIRMED`: historical memo-level ticker fanout is proven by current code history artifacts, writer-path shape, and retained report manifests.
- `SURFACING_CONFIRMED` applies if contaminated rows remain active under ticker scope.
- `CLEANUP_BLOCKED`: cleanup still requires live inventory, backup/checksum, operator review, and a mutation-specific task card.

Memory live inventory read-only:

- Active DB path resolved to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite`.
- `memory_entries`: `2440` total, `147` active, `2293` expired/closed.
- Exact active cross-company duplicate normalized-statement/source clusters: `0`.
- Remaining review surface: `1` source-fanout threshold cluster, `14` deduped known historical rows, and `3` manual-review rows.
- Prior approved cleanup candidates are exhausted: `0` active, `963` expired/closed, `0` missing.

A2M News Trace / Entity-Linking Blast-Radius Audit:

- `A2M_TRACE_PARTIAL`.
- `ROOT_CAUSE_INFERRED`.
- `BLAST_RADIUS_MEDIUM`.
- `DATA_ACCESS_REQUIRED`.
- Likely retrieval/path-parity failure class: `/rag/query source=news` matches `ticker` or `tickers`, while backend chat `HybridRetriever("news_chunks")` and `_filter_news_by_ticker()` match only top-level `ticker`.

## Validation Plan

- Validate this task card.
- Stage only allowed task cards and report artifacts.
- Run cached diff name/status and stat checks.
- Run the allowlist leak check.
- Run `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/post_nvme_memory_a2m_audit_artifact_checkpoint_v1_20260519.md`.
- Run `git diff --cached --check`.
- Commit only if staged paths are exactly the allowed task/report artifacts.
- Release the registry claim after commit and verify final `list-active`.

## Project Memory Save Recommendation

`SAVE_RECOMMENDED`: Future Tenn sessions should remember that the post-NVMe audit artifacts for Cockpit route orchestration, control-prompt guard tests, gold metric coverage, memory contamination, live memory inventory, and A2M news trace were checkpointed together in the active NVMe runtime branch as report/task-card artifacts only. The checkpoint intentionally did not rerun DB, Qdrant, runtime, APEX, Home, extraction, or news validation.
