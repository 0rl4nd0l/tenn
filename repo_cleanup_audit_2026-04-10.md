# Tenn Repo Cleanup Audit

Date: 2026-04-10
Mode: Report-only

## 1. Executive Summary

- Repo state risk level: HIGH
- Whether destructive cleanup is safe: NO
- Whether only report-only cleanup is appropriate: YES

Confirmed:
- No destructive cleanup commands were executed.
- No files were deleted, reset, pruned, stashed, or overwritten.
- Report-only is the correct outcome because the worktree is active, overlaps current backend/cockpit extraction work, and multiple linked worktrees are live.

## 2. Inventory

### Branch State

- Current branch: `cloud/session-20260319`
- Current status: `## cloud/session-20260319...origin/cloud/session-20260319 [ahead 70]`
- Staged tracked files: none
- Unstaged tracked files: active across docs, backend, cockpit, tests, config, and scripts
- Deleted tracked files: `asx_data`
- Untracked non-ignored files: 45

### Tracking Branches

- `cloud/session-20260319` tracks `origin/cloud/session-20260319`
- `main` tracks `origin/main`
- Most `agent/*` and `vk/*` branches shown locally do not show upstream tracking in `git branch -vv`

### Local Branches

- `cloud/session-20260319`
- `main`
- `agent/backend-b525b431`
- `agent/task_01121167-7a32-496c-9a99-b32c5da516be`
- `agent/task_0a27507a-04fb-42ac-906a-7f8c2282761c`
- `agent/task_235bcf6c-a212-4ed3-9b4d-5165c2c0e917`
- `agent/task_5d3b6b29-7e6f-41eb-b596-54d0d1b03e10`
- `agent/task_87837021-ac3a-4ab2-881d-9b6021d1e1a5`
- `agent/task_bf4f828d-5835-41dd-af28-801aaf456597`
- `agent/task_e0a002d0-dfeb-421d-ad9c-4ec1f43f9498`
- `agent/task_e168e316-2221-4828-9616-6a2f07f0bfae`
- `agent/task_ef414e7e-697b-4b58-b77d-6eb2a732765f`
- `agent/task_fb4ca913-53e2-410b-ae35-f7358f25e513`
- `vk/08c6-determine-pdf-me`
- `vk/3baa-pdf-extraction-a`

### Worktree State

- Main worktree: `/mnt/sdb2/home/l4nd0/tenn`
- Secondary `main` worktree: `/mnt/sdb2/home/l4nd0/tenn-main-reconcile`
- 10 `agent/task_*` worktrees under `agent-orchestrator/.data/worktrees/`
- 3 registered worktree entries report `prunable gitdir file points to non-existent location`
- No worktrees were touched

### Stash State

- No stashes

### In-Progress Git Operations

- No merge in progress
- No rebase in progress
- No cherry-pick in progress
- No lockfiles or sequencer markers were found in `.git`

### Recent Commits

- `1818b16 milestone(intel-ops): connected Intel Pulse to real backend services`
- `26781ff milestone(intel-ops): implemented Intel Pulse observability surface`
- `9b7773c milestone(cockpit-news): restore newspaper4k manual ingest runtime`
- `abf10dc milestone(cockpit-routing): defer chat to API under GPU contention`
- `a9a935c milestone(cockpit-ui): fix manual news ingest action routing`

### Modified Tracked Files

Root/docs/config:
- `.gitignore`
- `.mcp.json`
- `README.md`
- `docs/architecture/00_README.md`
- `docs/architecture/02_runtime_topology.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/architecture/19_backend_api_surface.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/claude/STATE.md`
- `docs/claude/current-state.md`
- `docs/claude/gap-analysis.md`
- `docs/claude/lessons.md`
- `docs/extraction/metric_extraction_contract.md`
- `docs/research/README.md`
- `docs/setup/environment.md`
- `docs/setup/runtime.md`
- `docs/startup.md`

Backend active implementation:
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/services/extraction_review.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`

Backend test/config:
- `financial-engine_v2/backend/pytest.ini`
- `financial-engine_v2/backend/requirements-dev.txt`
- multiple backend test files under `financial-engine_v2/backend/tests/`

Cockpit active implementation:
- multiple files under `financial-engine_v2/cockpit/core/`
- multiple files under `financial-engine_v2/cockpit/integrations/`
- `financial-engine_v2/cockpit/storage/state.py`
- `financial-engine_v2/cockpit/ui/app.py`
- `financial-engine_v2/cockpit/ui/screens.py`
- multiple cockpit tests under `financial-engine_v2/cockpit/tests/`

Runtime/config/scripts:
- `financial-engine_v2/config/cockpit.yaml`
- `financial-engine_v2/config/cockpit_llm.yaml`
- `financial-engine_v2/docker-compose.yml`
- `financial-engine_v2/scripts/extraction_eval_scorecard.py`
- `financial-engine_v2/scripts/run_local_backend.sh`
- several cockpit-related test scripts
- `scripts/cockpit`
- `scripts/load_news_to_qdrant.py`
- several test scripts under `scripts/`

### Deleted Tracked Files

- `asx_data`

### Untracked Files

New docs/research:
- `docs/extraction_cloud_testing.md`
- `docs/research/cockpit_company_analysis_investigation_2026-04-09.md`
- `docs/research/tenn_external_resource_implementation_planning.md`
- `docs/research/tenn_external_resource_viability_investigation.md`

New backend implementation:
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py`

New eval fixtures:
- `financial-engine_v2/backend/tests/fixtures/extraction_eval/*.json`
- `financial-engine_v2/backend/tests/fixtures/extraction_gold/*.json`

New backend tests:
- several `financial-engine_v2/backend/tests/test_*.py`

New cockpit tests:
- several `financial-engine_v2/cockpit/tests/test_*.py`

New shared code:
- `financial-engine_v2/shared/__init__.py`
- `financial-engine_v2/shared/session_memory_base.py`

New scripts:
- `financial-engine_v2/scripts/extraction_gold_eval_scorecard.py`
- `scripts/analyze_real_extraction_eval_duckdb.py`
- `scripts/run_real_extraction_eval.py`
- `scripts/run_real_extraction_eval_mlflow.py`
- `scripts/setup_eval_cloud.sh`
- `scripts/test_run_real_extraction_eval.py`

Runtime/artifact-like untracked:
- `financial-engine_v2/data/`
- `financial-engine_v2/worker/celerybeat-schedule`
- `nohup.out`

### Ignored-But-Notable Paths

- `financial-engine_v2/data` about `150G`
- `backups` about `56G`
- `.archives` about `37G`
- `models` about `21G`
- `reports` about `3.5G`
- `notebooks` about `227M`
- `exports` about `207M`
- `agent-orchestrator/.data/worktrees` about `114M`
- `.opencode` about `8.5M`
- `.claude` about `3.7M`
- `data` about `2.4M`
- `.ruff_cache` about `728K`
- `.pytest_cache` about `340K`

### Also Identified

Likely active implementation files:
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/services/extraction_review.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/api/routes.py`
- multiple `financial-engine_v2/cockpit/core/*`
- multiple `financial-engine_v2/cockpit/integrations/*`

Likely generated artifacts / logs / caches:
- `.pytest_cache/`
- `.ruff_cache/`
- `__pycache__/`
- `.coverage`
- `backend.log`
- `nohup.out`
- `financial-engine_v2/worker/celerybeat-schedule`

Likely reports and research artifacts:
- `docs/research/*`
- `reports/`
- `exports/`
- `TUI EVIDENCE/`
- `.claude/monitors/*`

Likely local datasets / eval outputs:
- `financial-engine_v2/data/`
- `data/`
- backend eval fixture directories
- `mlruns/`

Likely notebooks / scratch work:
- `notebooks/`

Duplicated or near-duplicated artifact folders:
- repeated `ui-ux-pro-max` skill/data trees across hidden tool directories such as `.agents/`, `.augment/`, `.claude/`, `.codebuddy/`, `.codex/`, `.continue/`, `.cursor/`, `.factory/`, `.gemini/`, `.kiro/`

## 3. Classification Table

| Path | Category | Rationale | Action Recommendation |
|---|---|---|---|
| Current dirty worktree on `cloud/session-20260319` | A. ACTIVE_WORK | Active tracked and untracked changes across docs, backend, cockpit, tests, scripts | KEEP |
| `asx_data` | A. ACTIVE_WORK | Tracked deletion with unknown intent; could be deliberate work | DO_NOT_TOUCH |
| `docs/extraction_cloud_testing.md` | A. ACTIVE_WORK | New doc tied to current extraction work | KEEP |
| `docs/research/*.md` | C. REPORT_OR_ARTIFACT | Human-authored investigations and planning docs | KEEP |
| `financial-engine_v2/backend/app/services/*.py` modified/new | A. ACTIVE_WORK | Direct overlap with extraction pipeline implementation | KEEP |
| `financial-engine_v2/backend/tests/test_*.py` modified/new | A. ACTIVE_WORK | Active regression/test work tied to current code changes | KEEP |
| `financial-engine_v2/backend/tests/fixtures/extraction_eval/*.json` | D. LOCAL_DATASET_OR_EVAL_OUTPUT | Eval fixtures for active extraction evaluation | KEEP |
| `financial-engine_v2/backend/tests/fixtures/extraction_gold/*.json` | D. LOCAL_DATASET_OR_EVAL_OUTPUT | Gold eval fixtures; evidence inputs | KEEP |
| `financial-engine_v2/cockpit/**` modified/new | A. ACTIVE_WORK | Live cockpit implementation and tests | KEEP |
| `financial-engine_v2/shared/` | A. ACTIVE_WORK | New shared code, likely part of current implementation | KEEP |
| `financial-engine_v2/data/` | D. LOCAL_DATASET_OR_EVAL_OUTPUT | Large local dataset/eval tree; not safe to infer disposability | DO_NOT_TOUCH |
| `data/` | D. LOCAL_DATASET_OR_EVAL_OUTPUT | Local DB/data/reports/resource library | DO_NOT_TOUCH |
| `reports/` | C. REPORT_OR_ARTIFACT | Evidence and evaluation outputs | DO_NOT_TOUCH |
| `exports/` | C. REPORT_OR_ARTIFACT | Exported chats and manifests | DO_NOT_TOUCH |
| `notebooks/` | F. MAYBE_SAFE_TO_ARCHIVE | Scratch/research surface with its own `.git/`; not safe to auto-remove | ARCHIVE_LATER |
| `backups/` | C. REPORT_OR_ARTIFACT | Explicit backup store | DO_NOT_TOUCH |
| `.archives/` | C. REPORT_OR_ARTIFACT | Explicit archive store | DO_NOT_TOUCH |
| `models/` | H. DATA_MISSING_DO_NOT_TOUCH | Local model assets may be required by runtime | DO_NOT_TOUCH |
| `agent-orchestrator/.data/worktrees/` | A. ACTIVE_WORK | Live linked worktrees | DO_NOT_TOUCH |
| Prunable worktree metadata entries | H. DATA_MISSING_DO_NOT_TOUCH | Need explicit audit before any prune/remove action | DO_NOT_TOUCH |
| `.claude/monitors/*` | C. REPORT_OR_ARTIFACT | Monitoring logs/history are evidence | DO_NOT_TOUCH |
| `.claude/settings.local.json` and `.claude/deer-flow/.env` | H. DATA_MISSING_DO_NOT_TOUCH | Local config/secret-bearing files | DO_NOT_TOUCH |
| `financial-engine_v2/worker/celerybeat-schedule` | H. DATA_MISSING_DO_NOT_TOUCH | Runtime schedule state; not safe to delete on assumption | DO_NOT_TOUCH |
| `nohup.out` | H. DATA_MISSING_DO_NOT_TOUCH | Root-owned runtime output file; ownership and provenance unclear | DO_NOT_TOUCH |
| `.pytest_cache/` | G. SAFE_TO_DELETE | Standard recreatable pytest cache | SAFE_DELETE |
| `.ruff_cache/` | G. SAFE_TO_DELETE | Standard recreatable ruff cache | SAFE_DELETE |
| `__pycache__/` directories | G. SAFE_TO_DELETE | Standard Python bytecode caches | SAFE_DELETE |
| `.opencode/node_modules/` | E. REGENERABLE_CACHE | Reinstallable, but local tooling may rely on it right now | DO_NOT_TOUCH |
| Local virtualenvs like `.venv*` | E. REGENERABLE_CACHE | Rebuildable, but may be in active use | DO_NOT_TOUCH |
| Repeated hidden `ui-ux-pro-max` trees | F. MAYBE_SAFE_TO_ARCHIVE | Duplication exists, but tool ownership/usage not fully audited | ARCHIVE_LATER |

## 4. Safe Actions Taken

- Cleanup actions taken: none
- Exact cleanup commands run: none
- Exact paths affected: none
- Why: collision risk is high, so the correct action under the stated rules is report-only

Read-only audit commands run:
- `git status --short --branch`
- `git branch -vv`
- `git worktree list --porcelain`
- `git stash list`
- `git log --oneline --decorate -n 5`
- `git diff --name-status`
- `git diff --cached --name-status`
- `git ls-files --others --exclude-standard`

## 5. Not Touched

- Entire active dirty worktree on `cloud/session-20260319`
- `asx_data`
- All `agent/task_*` branches and worktrees
- `main` worktree in `/mnt/sdb2/home/l4nd0/tenn-main-reconcile`
- The 3 prunable worktree metadata entries
- `financial-engine_v2/data/`
- `data/`
- `reports/`
- `exports/`
- `notebooks/`
- `backups/`
- `.archives/`
- `models/`
- `.claude/*`
- `.opencode/node_modules/`
- local virtualenv directories
- `financial-engine_v2/worker/celerybeat-schedule`
- `nohup.out`
- repeated hidden `ui-ux-pro-max` directories

## 6. Recommended Next Cleanup Steps

1. Freeze concurrent work first. Do not attempt cleanup while `cloud/session-20260319` is actively moving.
2. Decide the intent of `asx_data` before touching anything else.
3. Review the 45 untracked non-ignored files and either commit them or explicitly classify them as archive candidates.
4. If you want one minimal cleanup pass later, limit it strictly to `.pytest_cache/`, `.ruff_cache/`, and known `__pycache__/` directories.
5. Audit the 3 prunable worktree entries with branch-owner confirmation before any prune/remove operation.
6. Treat `financial-engine_v2/worker/celerybeat-schedule` and `nohup.out` as runtime artifacts until the owning process and retention need are confirmed.
7. Treat `financial-engine_v2/data/`, `data/`, `reports/`, `exports/`, `backups/`, `.archives/`, `models/`, and `notebooks/` as retention-review items, not cleanup targets.
8. If desired, prepare an approval-gated archive plan for duplicated hidden tool skill trees rather than deleting them.

## 7. Final Status

Post-cleanup `git status` at audit time:

```text
## cloud/session-20260319...origin/cloud/session-20260319 [ahead 70]
 M .gitignore
 M .mcp.json
 M README.md
 D asx_data
 M docs/architecture/00_README.md
 M docs/architecture/02_runtime_topology.md
 M docs/architecture/12_evaluation_and_drift_monitoring.md
 M docs/architecture/19_backend_api_surface.md
 M docs/architecture/SYSTEM_CONTRACT.md
 M docs/claude/STATE.md
 M docs/claude/current-state.md
 M docs/claude/gap-analysis.md
 M docs/claude/lessons.md
 M docs/extraction/metric_extraction_contract.md
 M docs/research/README.md
 M docs/setup/environment.md
 M docs/setup/runtime.md
 M docs/startup.md
 M financial-engine_v2/CLAUDE.md
 M financial-engine_v2/backend/app/api/routes.py
 M financial-engine_v2/backend/app/main.py
 M financial-engine_v2/backend/app/services/docling_extract.py
 M financial-engine_v2/backend/app/services/extraction_review.py
 M financial-engine_v2/backend/app/services/multipass_extraction.py
 M financial-engine_v2/backend/app/services/pipeline.py
 M financial-engine_v2/backend/pytest.ini
 M financial-engine_v2/backend/requirements-dev.txt
 M financial-engine_v2/backend/tests/test_backend_api_client_context.py
 M financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
 M financial-engine_v2/backend/tests/test_cockpit_api_models.py
 M financial-engine_v2/backend/tests/test_context_endpoints.py
 M financial-engine_v2/backend/tests/test_extraction_eval_harness.py
 M financial-engine_v2/backend/tests/test_extraction_llm_separation.py
 M financial-engine_v2/backend/tests/test_multipass_extraction.py
 M financial-engine_v2/cockpit/core/actions.py
 M financial-engine_v2/cockpit/core/agent/anthropic_client.py
 M financial-engine_v2/cockpit/core/agent/hybrid_router.py
 M financial-engine_v2/cockpit/core/agent_loop.py
 M financial-engine_v2/cockpit/core/chat.py
 M financial-engine_v2/cockpit/core/config.py
 M financial-engine_v2/cockpit/core/conversation_commands.py
 M financial-engine_v2/cockpit/core/plotly_html.py
 M financial-engine_v2/cockpit/core/session_memory.py
 M financial-engine_v2/cockpit/core/tool_definitions.py
 M financial-engine_v2/cockpit/core/tool_executor.py
 M financial-engine_v2/cockpit/core/tools.py
 M financial-engine_v2/cockpit/integrations/backend_api.py
 M financial-engine_v2/cockpit/integrations/llamacpp_client.py
 M financial-engine_v2/cockpit/integrations/llamacpp_manager.py
 M financial-engine_v2/cockpit/integrations/qual_context.py
 M financial-engine_v2/cockpit/storage/state.py
 M financial-engine_v2/cockpit/tests/test_agent_stress.py
 M financial-engine_v2/cockpit/tests/test_anthropic_client.py
 M financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py
 M financial-engine_v2/cockpit/tests/test_hybrid_router.py
 M financial-engine_v2/cockpit/tests/test_llamacpp_manager_router_mode.py
 M financial-engine_v2/cockpit/tests/test_llm_backend_readonly_format.py
 M financial-engine_v2/cockpit/tests/test_router_edge_cases.py
 M financial-engine_v2/cockpit/tests/test_slash_commands.py
 M financial-engine_v2/cockpit/tests/test_tool_executor_extraction.py
 M financial-engine_v2/cockpit/ui/app.py
 M financial-engine_v2/cockpit/ui/screens.py
 M financial-engine_v2/config/cockpit.yaml
 M financial-engine_v2/config/cockpit_llm.yaml
 M financial-engine_v2/docker-compose.yml
 M financial-engine_v2/scripts/extraction_eval_scorecard.py
 M financial-engine_v2/scripts/run_local_backend.sh
 M financial-engine_v2/scripts/test_cockpit_news_qual_context.py
 M financial-engine_v2/scripts/test_cockpit_plotly_html.py
 M financial-engine_v2/scripts/test_cockpit_price_history_chat.py
 M financial-engine_v2/scripts/test_cockpit_tools_additional_context.py
 M scripts/cockpit
 M scripts/load_news_to_qdrant.py
 M scripts/test_cockpit_launcher_helpers.py
 M scripts/test_load_news_qdrant_corpus_payload.py
 ?? docs/extraction_cloud_testing.md
 ?? docs/research/cockpit_company_analysis_investigation_2026-04-09.md
 ?? docs/research/tenn_external_resource_implementation_planning.md
 ?? docs/research/tenn_external_resource_viability_investigation.md
 ?? financial-engine_v2/backend/app/services/method_isolated_extraction.py
 ?? financial-engine_v2/backend/tests/fixtures/extraction_eval/...
 ?? financial-engine_v2/backend/tests/fixtures/extraction_gold/...
 ?? financial-engine_v2/backend/tests/test_*.py
 ?? financial-engine_v2/cockpit/tests/test_*.py
 ?? financial-engine_v2/data/
 ?? financial-engine_v2/scripts/extraction_gold_eval_scorecard.py
 ?? financial-engine_v2/shared/
 ?? financial-engine_v2/worker/celerybeat-schedule
 ?? nohup.out
 ?? scripts/analyze_real_extraction_eval_duckdb.py
 ?? scripts/run_real_extraction_eval.py
 ?? scripts/run_real_extraction_eval_mlflow.py
 ?? scripts/setup_eval_cloud.sh
 ?? scripts/test_run_real_extraction_eval.py
```

What remains unresolved:
- 1 tracked deletion with unknown intent: `asx_data`
- substantial active implementation changes across backend, cockpit, docs, tests, and scripts
- 45 untracked non-ignored paths
- multiple live worktrees
- 3 prunable worktree metadata entries requiring manual audit
- large local data/artifact stores requiring retention review, not cleanup

Whether manual review is required: YES
