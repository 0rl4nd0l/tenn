# Key Decisions

This doc records architectural and operational decisions that have been formalized in the repo. It does not replace the source docs — it surfaces the decisions in one place for quick orientation.

## Source Trace
- `docs/entrypoints.md` (Confirmed)
- `docs/architecture/01_system_overview.md` (Confirmed)
- `docs/architecture/02_runtime_topology.md` (Confirmed)
- `docs/architecture/09_worker_and_celery_contract.md` (Confirmed — referenced)
- `docs/architecture/13_security_and_secrets.md` (Confirmed)
- `docs/ops/README.md` (Confirmed)
- `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md` (Confirmed — referenced)
- `financial-engine_v2/README.md` (Confirmed)
- `docs/cloud_workflow.md` (Confirmed)

---

## Decision Table

| # | Decision | Rationale | Source |
|---|----------|-----------|--------|
| D-01 | `run_local_backend.sh` is the only canonical entrypoint for agents | Deterministic, no hidden dependencies (unlike Docker or Cockpit) | `docs/entrypoints.md` |
| D-02 | `docker compose` is SUPPORTED but PROHIBITED for agents by default | Adds Docker daemon + service startup surface; increases nondeterminism | `docs/entrypoints.md` |
| D-03 | Cockpit TUI is SUPPORTED but PROHIBITED for agents by default | Interactive UI layer increases nondeterminism for automated contexts | `docs/entrypoints.md` |
| D-04 | `python run.py` is SUPPORTED (batch) but not a system bootstrap signal | Runs batch workflows; does not deterministically indicate "API is up" | `docs/entrypoints.md` |
| D-05 | Local launcher forces `DATA_ROOT` to repo `data/` by default | Prevents accidental Docker `/data/...` paths in local mode | `financial-engine_v2/README.md` |
| D-06 | llama.cpp preferred over Ollama for agent/coding workflows | Performance characteristics and session stability; Ollama governs financial-engine backend only | `docs/ops/README.md`, `docs/ops/openclaw_ops_loop.md` |
| D-07 | Self-optimizing model router with weighted scoring | Balances latency (0.4), throughput (0.3), error (0.2), queue (0.1), gpu (0.1) across finance-aware task detection | `docs/architecture/01_system_overview.md` |
| D-08 | Vector IDs are deterministic | Enables deduplication on upsert without re-fetching existing vectors | `docs/architecture/06_embeddings_and_vector_store.md` (referenced) |
| D-09 | `commentary_chunks` is the chat RAG collection (not `asx_docs`) | Historical naming distinction; `asx_docs` is a different collection | `docs/current_system.md`, `financial-engine_v2/README.md` |
| D-10 | Secrets are never stored in repo; host-local files only | `.env` is .gitignored; OpenClaw config is in `~/.openclaw/`; llama.cpp overrides in `~/.config/tenn/` | `docs/architecture/13_security_and_secrets.md` |
| D-11 | OpenAI planner auth bootstrapped from 1Password | Avoids embedding credentials in repo files | `docs/architecture/13_security_and_secrets.md` |
| D-12 | Phase 1 Compose blueprint does NOT replace existing `docker-compose.yml` | Additive; tested successor required before replacement | `docs/ops/README.md` |
| D-13 | Local source of truth for Cloud workflow | Cloud sees only committed, pushed state; never uncommitted edits or local services | `docs/cloud_workflow.md` |
| D-14 | One subsystem per Cloud task / PR | Keeps review scope narrow and reversible | `docs/cloud_workflow.md` |
| D-15 | CPU fallback is supported but not normalized in guidance | GPU-first is the expected production path; CPU fallback is a degraded mode | `docs/ops/README.md` |
| D-16 | Engineering discipline requires plan before implementation | Prevents architecture drift; enforces invariant review and test execution | `docs/architecture/11_engineering_discipline.md` |

---

## Conflicts and Ambiguities

No confirmed conflicts between source docs were found during the 2026-03-20 audit.

**Potential ambiguity:** `docs/current_system.md` quick start lists `python run.py` as the post-pull command, but `docs/entrypoints.md` prohibits this for agents. These are consistent: `run.py` is valid for operator batch workflows, not for agent system bootstrap. If in doubt, use `run_local_backend.sh`.

---

## Decisions Not Yet Formalized

The following are Inferred from code/docs patterns but not yet written as explicit decisions:

- Specific retry/backoff policy for LLM failures (referenced in `10_failure_model.md` but details not confirmed here)
- Exact vector baseline comparison thresholds
- Explicit policy for `commentary_chunks_v2` fallback triggering conditions

These are tracked in [gap-analysis.md](gap-analysis.md).
