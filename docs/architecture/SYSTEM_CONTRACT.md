# SYSTEM CONTRACT — TENN / FINANCIAL ENGINE

Status: normative architecture contract for reconciliation and future changes.

This document is the architectural source of truth for `main` during incremental reconciliation. It is intentionally conservative: it states the rules the system must follow, but it does not imply that every migration from `cloud/session-20260319` has already landed.

## 1. Authority

- Backend is the sole authority for ingestion, extraction, structured financial storage, vector storage, and retrieval behavior.
- Client and operator surfaces must consume authoritative data through backend-owned interfaces.
- Do not introduce direct client-side retrieval, direct Qdrant writes outside backend-owned flows, or competing sources of truth.

## 2. Mandatory Flow

The intended system flow remains:

`ingestion -> extraction -> normalization -> embeddings/storage -> analysis/reporting -> client`

Rules:

- Do not skip layers.
- Do not blend extraction with analysis.
- Do not move retrieval logic into cockpit or UI surfaces.
- Do not create parallel pipelines that silently diverge from the backend.

## 3. Extraction Rules

- Preserve structural fidelity of source documents.
- Financial metric extraction must remain exact, explicit, and deterministic.
- Do not infer missing values.
- Do not substitute guessed metrics when extraction is ambiguous.
- If explicit financial data is unavailable, return `null` or an explicit failure state rather than fabricating output.
- The only permitted derivation is explicit Appendix 5B capex subtotal summation when the source itself provides the sub-items.

## 4. Storage And Vector Invariants

- No schema changes during conservative reconciliation unless explicitly approved.
- Vector IDs must remain deterministic.
- Embedding dimension mismatches must fail fast rather than silently rerouting to alternate collections.
- Do not introduce fallback embedding backends or multi-model vector semantics without migration planning.

## 5. Retrieval Boundary

- Backend owns retrieval.
- Do not reintroduce direct client-side ranking, Qdrant access, or mixed retrieval implementations.
- New retrieval routes, route rewrites, or contract changes are out of scope for first-wave reconciliation and require explicit review.

## 6. Worker Contract

- `financial-engine_v2/backend/app/worker_tasks.py` is the canonical worker surface to evolve.
- `financial-engine_v2/worker/app/tasks.py` is legacy and must not be expanded during first-wave reconciliation.
- Preserve existing task names and working behavior unless a later narrow migration is validated end-to-end.

## 7. Runtime And Entrypoints

- `financial-engine_v2/scripts/run_local_backend.sh` is the canonical local backend launcher.
- Helper scripts may wrap the canonical launcher, but they must not redefine system authority or bootstrap a competing runtime.
- Launcher rewrites are high-risk because they change operational behavior; treat them separately from documentation adoption.

## 8. GPU Process Safety

- If a task spawns or restarts `llama-server`, it must reuse the healthy canonical instance when possible.
- Use `scripts/gpu_process_guard.sh --check` before spawning or restarting llama.cpp services.
- Do not spawn independent rogue `llama-server` processes on arbitrary ports.

## 9. Agent Change Rules

Before backend, extraction, retrieval, worker, or launcher changes:

1. State the target layer.
2. State the relevant invariants.
3. State what must not change.
4. Explain why the change is safe.
5. Stop if the change requires guessing about schema, retrieval, embeddings, or runtime semantics.

## 10. Reconciliation Rule

During incremental merge work from `cloud/session-20260319` into `main`:

- Prefer omission over risky adoption.
- Prefer additive preservation over destructive replacement.
- Do not delete legacy or overlapping files unless replacement behavior is confirmed and validated.
- Missing evidence is a stop signal for broad or destructive edits.

## Final Principle

Correctness, determinism, and traceability outrank cleanliness, breadth, and speed.
