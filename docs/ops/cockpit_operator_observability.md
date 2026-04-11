# Cockpit operator observability (quick links)

Link-only runbook: each row answers one operator question by pointing at **commands**, **routes**, or **architecture docs**. No secrets in this file.

**Acceptance:** you can complete every row using only this page and the linked targets.

**Profile note:** `LOCAL_BACKEND_PROFILE=isolated` (see `financial-engine_v2/CLAUDE.md`) starts a **minimal** backend — Qdrant, embeddings, and extraction may be **off**. A failing RAG or embed check in isolated mode is often **expected**, not a production regression. Use **`full`** (or Docker compose full stack) when validating RAG, Qdrant, and extraction together. Canonical boot: `docs/entrypoints.md`.

| Question | How | Where to read the answer |
|----------|-----|---------------------------|
| Is the API process up? | `curl -sS http://127.0.0.1:8000/api/health` (adjust host/port) | JSON body / HTTP status |
| Is aggregated Cockpit health OK? | `curl -sS http://127.0.0.1:8000/api/cockpit/health` | `financial-engine_v2/backend/app/routes/cockpit_api.py` (`cockpit_health`) |
| What does the **web UI** use for health? | Open same-origin `/api/cockpit/health` on the Next app (proxies/augments backend + host; see code) | `cockpit-ui/app/api/cockpit/health/route.ts` |
| Is extraction active / mutex held? | `curl -sS http://127.0.0.1:8000/api/cockpit/config` | JSON: `extraction_active`, `extraction_active_runs`, `extraction_activity_source`, etc. |
| GPU topology / rogue processes / VRAM? | `bash scripts/gpu_process_guard.sh --check` from repo root | Script exit code and stdout; see `docs/architecture/SYSTEM_CONTRACT.md` GPU sections |
| Last RAG stability summary? | Run `python financial-engine_v2/scripts/evaluate_rag_stability.py` (read-only; needs reachable backend for queries) | `financial-engine_v2/reports/rag_stability/latest_summary.json` |
| RAG stability procedure context? | Read architecture doc | `docs/architecture/12_evaluation_and_drift_monitoring.md` |
| Active embedding model guard file? | After backend run, read file if present | `financial-engine_v2/reports/runtime_embedding_model.txt` (see `financial-engine_v2/backend/app/main.py`) |
| Vector baseline present / verify? | `python financial-engine_v2/scripts/verify_vector_baseline.py` | `docs/architecture/11_rebuild_and_recovery.md`, `financial-engine_v2/reports/vector_baseline.json` (created by rebuild flow) |
| Cockpit contract vs code / surfaces? | Read addendum | `docs/architecture/21_cockpit_client_contract.md` |
| Full backend route list? | Read inventory | `docs/architecture/19_backend_api_surface.md` |

### Consumer pattern (reminder)

- **Scripts and operators:** prefer the **backend** base URL for stable checks.
- **Browser UI:** uses Next BFF routes under `cockpit-ui/app/api/cockpit/`; see `docs/architecture/21_cockpit_client_contract.md` §3.
