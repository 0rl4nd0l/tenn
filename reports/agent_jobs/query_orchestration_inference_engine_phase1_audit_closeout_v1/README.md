# Inference Engine Phase 1 Audit Closeout

Issue: https://github.com/0rl4nd0l/tenn/issues/138

## Decision

The released Phase 1 inference-engine audit artifact was incomplete. The preserved original task card required a detailed call-site and duplication audit, but its tracked evidence only contained `status.json` and `diff-check.json`, and its allowlist only permitted the task card plus those two files.

This closeout provides the missing report-only evidence from current repository state. It does not change product behavior.

## Confirmed Facts

- The current isolated base branch did not contain `docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_v1_20260529.md` or `reports/agent_jobs/query_orchestration_inference_engine_phase1_audit_v1_20260529/`.
- The live shared checkout contained the preserved original task card and only `status.json` / `diff-check.json` for that job.
- Local commit `8f7a0ab7` preserves the stale Phase 1 audit card plus status/diff-check artifacts.
- Local commit `b6a0cbd2` preserves a separate inference blocker audit bundle.
- No exact duplicate PR for #138 was found. PR #149 parks stale query-audit preservation and is adjacent, not the detailed Phase 1 closeout.

## Current Architecture Summary

- `financial-engine_v2/backend/app/services/llm.py` is the main backend LLM facade for routed JSON generation and embeddings.
- `financial-engine_v2/backend/app/services/router.py` classifies requests and returns `RoutingDecision` objects with role, model, provider, queue, task type, GPU utilization, queue depth, and confidence.
- `generate_json()` calls `route_request()`, executes llama.cpp JSON generation via `generate_json_llamacpp()`, records router metrics, and may reroute/fallback on selected failures.
- `embed_texts()` calls `route_request()` with embedding metadata and then delegates to `embed_texts_batched()`.
- Celery task routing separately calls `route_request()` for `llm_generate_json`, so a request may be routed once at queue dispatch and again inside the worker facade.
- Several backend module D2 paths still call `generate_json_llamacpp()` directly instead of `generate_json()`.
- Cockpit chat/agent paths use `LlamaCppClient` / Anthropic-compatible clients outside the backend inference facade.

## Metadata and Runtime Overrides

Router classification consumes:

- `task_type`, `request_type`, `operation`, `intent`
- `financial_task_type`, `analysis_type`
- `document_type`, `source_type`
- `retrieved_context_chars`, `document_count`
- `ticker`, `tickers`, `company`, `companies`
- `deep_reasoning`
- `repo_path`, `repository_path`, `file_path`, `workspace_path`, `path`, `cwd`
- `is_embedding`, `task`

Runtime override paths consume:

- `component`
- `requested_base_url`
- `requested_model`
- `llm_url`
- `llm_model`
- `embedding_model`
- `text_count`

Special component handling:

- `multipass_extraction`, `commentary_memo_extractor`, and `news_memo_extractor` resolve through `resolve_extraction_runtime_config()`.
- `commentary_memo_extractor` and `news_memo_extractor` force llama.cpp and disable fallback rerouting.
- `tenn_chat` passes `requested_base_url` but does not force llama.cpp, so Anthropic fallback can still occur when configured.

## Fallback Responsibilities

- `router.py` owns request classification and static/adaptive model/queue role selection.
- `llm.py` owns routed execution, metrics recording, retry/reroute eligibility, and last-resort Anthropic JSON fallback.
- `llamacpp_runtime.py` owns concrete runtime URL/model/header resolution, model verification, and llama.cpp JSON request parsing.
- `embeddings.py` owns embedding backend selection and switches between Ollama and llama.cpp embedding calls.
- Callers such as `tenn_chat.py` and module D2 paths own domain-specific degraded payloads or `None` returns.

## Leakage and Compatibility Risks

- Direct `generate_json_llamacpp()` calls in backend modules bypass `route_request()`, router metrics, queue policy, and `llm.py` fallback behavior.
- Cockpit agent/chat clients are separate runtime clients and should not be silently folded into the backend facade without a Cockpit contract decision.
- Celery dispatch and worker execution both route `llm_generate_json`, which can produce queue/execution drift if runtime state changes between enqueue and execution.
- Metadata override keys are informal dictionaries, so migration must preserve all current key meanings before introducing typed request objects.
- `llm_fn` injection supports legacy callables without `metadata`, so hardening must preserve tests and external hooks that pass custom LLM functions.
- Script and test harness call sites exercise the facade and local embedding lookalikes outside product request paths; Phase 2 implementation should classify them separately from backend runtime callers.

## Safe Migration Seams

1. Add typed request/result dataclasses beside the existing facade without changing call sites.
2. Add adapters that convert current `metadata` dictionaries into typed request fields while preserving raw metadata.
3. Instrument direct bypasses as report-only first, then migrate one low-risk module D2 path at a time.
4. Keep Cockpit LlamaCppClient/Anthropic agent paths out of scope until a separate Cockpit runtime contract exists.
5. Keep Celery queue routing backward-compatible: dispatch routing must not conflict with worker execution routing.

## DATA_MISSING

- No live runtime, queue, GPU, or model probes were run for this report.
- No dynamic call graph was generated; the map is `rg` and targeted read-only file inspection.
- No Phase 2 implementation PR exists in this closeout.
- No product decision was made to merge Cockpit runtime clients into the backend inference facade.
- `graphify-out/GRAPH_REPORT.md` was absent from the isolated worktree.

## Validation Summary

Current validation is recorded in `validation.json` and `diff-check.json`. The bundle is report-only and does not modify product code.

## Files Inspected

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `financial-engine_v2/backend/app/services/llm.py`
- `financial-engine_v2/backend/app/services/router.py`
- `financial-engine_v2/backend/app/services/llamacpp_runtime.py`
- `financial-engine_v2/backend/app/services/embeddings.py`
- `financial-engine_v2/backend/app/services/llamacpp_embeddings.py`
- `financial-engine_v2/backend/app/celery_app.py`
- `financial-engine_v2/backend/app/worker_tasks.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/services/news_memo_extractor.py`
- `financial-engine_v2/backend/app/services/commentary_memo_extractor.py`
- `financial-engine_v2/backend/app/services/thesis_watchdog.py`
- `financial-engine_v2/backend/app/services/thesis_audit.py`
- `financial-engine_v2/backend/app/services/rag.py`
- `financial-engine_v2/backend/app/services/analysis_rag_adapter.py`
- `financial-engine_v2/backend/app/services/hybrid_retriever.py`
- `financial-engine_v2/backend/app/services/reranker.py`
- `financial-engine_v2/backend/app/services/framework_classifier.py`
- `financial-engine_v2/backend/app/services/chat_quality_scorer.py`
- `financial-engine_v2/backend/app/modules/catalysts.py`
- `financial-engine_v2/backend/app/modules/moat.py`
- `financial-engine_v2/backend/app/modules/risk.py`
- `financial-engine_v2/backend/app/services/research_synthesis.py`
- `financial-engine_v2/backend/app/services/commentary_ingest.py`
- original preserved Phase 1 card/report artifacts in `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

## Commands Run

- `gh issue view 138 --repo 0rl4nd0l/tenn --json number,title,state,body,labels,url,comments`
- `gh pr list --repo 0rl4nd0l/tenn --state all --search "138 OR inference-engine Phase 1 audit report" --json number,title,state,url,headRefName,baseRefName`
- `gh pr list --repo 0rl4nd0l/tenn --state all --search "138 OR inference-engine Phase 1 audit report OR InferenceRequest OR InferenceResult" --json number,title,state,url,headRefName,baseRefName,updatedAt`
- `git worktree add -b audit/query-inference-engine-phase1-closeout-v1-20260601 ...`
- `pwd`, `date -Iseconds`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short --untracked-files=all`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/query_orchestration_inference_engine_phase1_audit_closeout_v1.md`
- `rg -n "\bgenerate_json\b" ...`
- `rg -n "\bembed_texts\b" ...`
- `rg -n "\broute_request\b" ...`
- `rg -n "\bllm_fn\b" ...`
- `rg -n "\bgenerate_json\b|\bembed_texts\b|\broute_request\b|\bllm_fn\b" financial-engine_v2 scripts -S --glob '!**/tests/**' --glob '!docs/**'`
- `python3 -m json.tool ...`
- `git diff --check`
- targeted `nl -ba` file inspections

## Final Status

- Lane: Query Orchestration
- Execution mode: audit_only
- Collision risk: LOW for report-only artifacts
- Product behavior changed: no
- Production data access: no
- Runtime/GPU/service restart: no
- Recommended PR link text: `Refs #138`
