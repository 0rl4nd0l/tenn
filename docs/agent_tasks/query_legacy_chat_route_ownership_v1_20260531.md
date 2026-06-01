---
job_id: query_legacy_chat_route_ownership_v1_20260531
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/README.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/route_ownership_matrix.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/current_route_inventory.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/followup_recommendation.md
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/status.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/validation.json
  - reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/diff-check.json
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# Task

Classify ownership for the live legacy `/chat` and `/api/chat` routes versus Cockpit's `/api/cockpit/chat` route before route-parity or source-label audits claim coverage across chat surfaces.

# GitHub tracking

- Issue: https://github.com/0rl4nd0l/tenn/issues/150
- PR link policy: use `Refs #150` or `audit for #150` unless product remediation lands and is validated separately.

# Target layer and contract

- Target layer: Query Orchestration route contract audit.
- Relevant contract rules: backend owns chat/retrieval authority; Cockpit web UI consumes backend APIs; source/evidence labels must stay honest; no alternate financial truth, memory, DB, Qdrant, news, runtime, GPU, parser, prompt, or gold-label mutation.
- What must not change: runtime chat behavior, evidence labels, source labels, route mounts, Cockpit streaming behavior, persisted chat/memory state, canonical financial truth, active Financial Truth canary artifacts.
- Safety basis: audit-only writes are limited to this task card and report bundle.

# Required preflight

Record:
- `pwd`
- `date -Iseconds`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --untracked-files=all`
- `git remote -v`
- `git worktree list --porcelain`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- registry claim/release if overlap is clear

# Inspection targets

Read only:
- `CLAUDE.md`
- `AGENTS.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/shared/evidence_labels.py`
- `cockpit-ui/next.config.mjs`
- `cockpit-ui/app/chat/route.ts`
- `cockpit-ui/app/full-chat/page.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/marketplace-assistant.ts`
- relevant backend/frontend tests and architecture docs for chat route ownership
- parked branch/report evidence for legacy chat evidence-envelope work

# Required analysis

Determine:
1. Which handler owns `POST /chat`.
2. Which handler owns `POST /api/chat`.
3. Which handler owns `POST /api/cockpit/chat`.
4. Which current UI clients call `/api/cockpit/chat`.
5. Whether any current UI client still calls the Next `/chat` proxy.
6. Whether legacy `/chat` and `/api/chat` currently expose a route-level `source_label_taxonomy_version` or compatibility evidence envelope.
7. Whether `chat_with_tenn()` emits source/evidence labels inside the legacy route content.
8. Whether Cockpit chat exposes richer source/evidence metadata and visible-source enforcement.
9. What regression tests currently cover each route family.
10. Whether parked legacy evidence-envelope branches/reports are already integrated into the current branch.
11. Which follow-up is safest: preserve and harden legacy routes, deprecate legacy routes, or leave data missing.

# Allowed writes

Only write:
- `docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/README.md`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/route_ownership_matrix.md`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/current_route_inventory.json`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/followup_recommendation.md`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/status.json`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/validation.json`
- `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/diff-check.json`

# Forbidden files and surfaces

Do not edit:
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `cockpit-ui/**`
- backend or frontend tests
- `docs/claude/STATE.md`
- active Financial Truth task-card/report artifacts
- production DB, Qdrant, news, memory, runtime, model, GPU, service config, parser routing, extraction prompts, or gold labels

# Hard stops

Stop and report only if:
- duplicate PR or tracker already covers this issue
- task-card validation fails
- registry overlap is active on the allowed write set
- implementation is required to satisfy the issue
- product route files would need edits in this audit
- production data access is required
- source/evidence labels would need to be weakened
- current route ownership cannot be determined from repo evidence

# Required output

Write the report bundle under `reports/agent_jobs/query_legacy_chat_route_ownership_v1_20260531/` with:
- route ownership matrix
- structured route inventory
- follow-up recommendation
- validation summary
- DATA_MISSING section
- commands run
- files inspected
- final status

# Validation

Run:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- registry claim/release around report writes if clear
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/query_legacy_chat_route_ownership_v1_20260531.md`
- JSON parse checks for generated JSON artifacts
- `git diff --check`
- `git diff --cached --check` before commit

# Definition of done

- Ownership for `/chat`, `/api/chat`, and `/api/cockpit/chat` is evidence-backed and recorded.
- Legacy route evidence-envelope status is clearly classified.
- Parked branch/report evidence is classified as integrated, not integrated, superseded, parked, or DATA_MISSING.
- Required follow-up is explicitly recommended without mutating route code.
- No forbidden surface is changed.
- Draft PR links the audit using `Refs #150`.
