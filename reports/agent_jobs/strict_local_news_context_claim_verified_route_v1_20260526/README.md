# Strict Local News Context Claim-Verified Route

## Classification

MERGED_AND_VALIDATED

## Summary

Prompts that explicitly ask to use `local_news_context` for a ticker now route
through the existing ticker news short-circuit. This preserves the same
`news_search` evidence shape used by `news for BHP`, so successful local-news
hits become `claim_verified + local_news_context` in the source pack.

No guard was weakened. No-hit and context-only local-news cases still return
guarded `DATA_MISSING`.

## Repo State

- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Canonical worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Isolated implementation branch: `safe/strict-local-news-context-claim-verified-route-v1-20260526`
- Isolated worktree: `/home/l4nd0/tenn-strict-local-news-context-claim-verified-route-v1-20260526`
- HEAD before implementation: `326b60db92bf286344c2bb90ed504ab5378a94a2`
- Implementation commit: `ca0e0e015e634fe4aa174b1b1e47df4561fd86ce`
- Final report commit: containing commit for this report bundle
- Merge method: isolated branch fast-forwarded into canonical with `git merge --ff-only safe/strict-local-news-context-claim-verified-route-v1-20260526`

## Files Changed

- `docs/agent_tasks/strict_local_news_context_claim_verified_route_v1_20260526.md`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/*`

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- DB, Qdrant, and news-store data files
- Parser routing, migrations, financial truth, memory, runtime/model/GPU config
- The unrelated canonical task cards:
  - `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
  - `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

## Runtime Smoke

Backend-only restart was performed because the running container predated the
canonical fast-forward and still served the old route behavior.

- Restart command: `docker compose -f financial-engine_v2/docker-compose.yml restart backend`
- Backend started after restart: `2026-05-26T02:34:30.151593406Z`
- Services not restarted: Qdrant, Postgres, worker, GPU worker, Next, llama-server

Smoke result summary:

- `Use only local_news_context for A2M`: PASS, `claim_verified_source_count=4`
- `Use only local_news_context for BHP`: PASS, `claim_verified_source_count=5`
- `Use only local_news_context for CSL`: PASS, `claim_verified_source_count=5`
- `Use only local_news_context for COH`: DATA_MISSING, no local-news hit
- `news for BHP`: PASS, `claim_verified_source_count=5`
- SSE `Use only local_news_context for BHP`: PASS, `claim_verified_source_count=5`

## Attestation

No DB, Qdrant, news-store, memory, financial truth, parser routing, migration,
projection rebuild/repair, runtime/model/GPU config, or broad UI mutation was
performed. The local-news honesty guard remains intact.

## Next Recommended Task

Consider a separate narrow follow-up for natural-language `latest local news
for TICKER` prompts that do not include the literal `local_news_context` token,
if product behavior should treat those as the same direct-news request.

## Project Memory Save Recommendation

Save that the safe fix for literal `local_news_context` ticker prompts is to
reuse the existing ticker news short-circuit in `cockpit/core/chat.py`; do not
mark context-only rows verified and do not change `chat_evidence_guard.py`.
