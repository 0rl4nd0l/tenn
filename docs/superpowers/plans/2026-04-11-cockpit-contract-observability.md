# Cockpit client contract and operator observability — implementation plan

> **Origin:** `docs/brainstorms/2026-04-11-cockpit-contract-observability-requirements.md` (see origin for problem frame, R1–R10, scope boundaries).  
> **Parent program:** Program Beta in `docs/superpowers/plans/2026-04-11-ideation-combinations.md`.  
> **For agentic workers:** Doc-only delivery; milestone commits per subsystem (`docs` / `architecture`). Use checkboxes to track.

**Goal:** Ship an architecture addendum plus conformance matrix and a link-only ops runbook so operators know **liveness vs Cockpit health**, where **extraction/GPU/RAG/embed** signals live, and how surfaces map to **`SYSTEM_CONTRACT.md`** — without new product features unless the matrix exposes a blocking gap (then file a follow-up).

**Non-goals:** Optional single-pane aggregator; Program Alpha; skill-tree deduplication. No secrets or real API keys in any new markdown.

---

## Requirements traceability

| ID | Requirement (summary) | Plan coverage |
|----|------------------------|---------------|
| R1 | Cockpit contract doc under `docs/architecture/` | Unit 1 |
| R2 | Pointer from `SYSTEM_CONTRACT.md` | Unit 1 |
| R3 | Liveness vs `/api/cockpit/health` behavior split | Unit 1 |
| R4 | Supported consumer patterns (backend vs Next BFF) | Unit 1 |
| R5 | No secrets in docs | All units + review checklist |
| R6–R7 | Conformance matrix with outcomes | Unit 2 |
| R8–R10 | Link-only runbook + profile note + dry-run criterion | Unit 3 |
| Success | STATE docs-governance item closable | Unit 4 |

---

## Key decisions (from origin; do not re-litigate without new input)

- **Addendum path:** `docs/architecture/21_cockpit_client_contract.md` (next free index after `20_chat_learning_loop.md`; avoids clashing with `19_backend_api_surface.md`). *(see origin: `docs/brainstorms/2026-04-11-cockpit-contract-observability-requirements.md`)*  
- **Runbook path:** `docs/ops/cockpit_operator_observability.md`  
- **Matrix placement:** Primary matrix lives **inside** `21_cockpit_client_contract.md` (one hop for reviewers); runbook **links** to that section anchor.

---

## File and index touch list

| Path | Action |
|------|--------|
| `docs/architecture/21_cockpit_client_contract.md` | Create — contract norms, health model, consumer patterns, surface inventory, conformance matrix |
| `docs/architecture/00_README.md` | Add index row for doc 21 |
| `docs/architecture/SYSTEM_CONTRACT.md` | Add short “See also” / table pointer under §1.2 (no duplication of full §1.2 text) |
| `docs/ops/cockpit_operator_observability.md` | Create — link-only table + profile note |
| `docs/ops/README.md` | Add bullet under a sensible section (e.g. “Cockpit / control plane”) linking the new runbook |
| `docs/claude/STATE.md` | Narrow or close docs-governance “Cockpit contract/code mismatch” with pointer to doc 21 + matrix |
| `docs/superpowers/plans/2026-04-11-ideation-combinations.md` | Optional one-line cross-link to this plan under Program Beta |

---

## Implementation units

### Unit 1 — Cockpit client contract (`21_cockpit_client_contract.md`)

**Deliverables**

- [ ] **Role:** Restate Cockpit as **client + orchestration only**, aligned with `docs/architecture/SYSTEM_CONTRACT.md` §1.2–§1.3 (authoritative reads via backend when configured; no parallel retrieval truth; Qdrant/Postgres rules as in contract — quote or paraphrase briefly, link to contract for full text).
- [ ] **Health model:** Document **minimal liveness** `GET /api/health` (canonical boot; matches `docs/entrypoints.md` and `financial-engine_v2/cockpit/integrations/backend_api.py` `health()`). Document **aggregated Cockpit health** `GET /api/cockpit/health` (`financial-engine_v2/backend/app/routes/cockpit_api.py`). State operator order: **liveness first**, then aggregated when debugging Cockpit dependencies.
- [ ] **Consumer patterns:** Operators/scripts → backend origin; browser UI → Next.js BFF routes under `cockpit-ui/app/api/cockpit/` (list known routes: `health`, `restart`, `action/execute`, `action/jobs/[jobId]`, `action/jobs/[jobId]/stop` — adjust if tree changes during implementation).
- [ ] **Representative backend surfaces:** Point to `financial-engine_v2/backend/app/routes/cockpit_api.py` and `BackendApiClient` for authoritative data methods (table or bullet list — not a full OpenAPI dump).
- [ ] **Streaming:** Pointer only: chat stream behavior covered by tests in `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py` (and related `test_cockpit_api_*.py` as appropriate).
- [ ] **Auth:** Name `X-API-Key` and env var names only; link `docs/architecture/13_security_and_secrets.md` for handling rules.

**Patterns to follow:** Tone and cross-linking like `docs/architecture/19_backend_api_surface.md` (inventory style) plus normative “MUST/MUST NOT” only where mirroring the contract.

**Test / review scenarios (documentation)**

- [ ] A reader finds **§1.2 pointer** from `SYSTEM_CONTRACT.md` in ≤2 clicks.
- [ ] No line in the new doc looks like a credential (grep for `sk-`, `Bearer `, long base64, or `.env` paste).

---

### Unit 2 — Conformance matrix (section inside doc 21)

**Deliverables**

- [ ] Build rows from **normative clauses** in `SYSTEM_CONTRACT.md` §1.2–§1.3 (group related bullets if the table would be huge). For each row: **clause (short label)** → **implementation pointers** (paths to `backend_api.py`, `cockpit_api.py`, `cockpit-ui/app/api/cockpit/*`, DbReader fallback notes) → **tests** (e.g. `financial-engine_v2/backend/tests/test_cockpit_api_*.py`, `financial-engine_v2/cockpit/tests/...` where relevant) → **outcome** `conform` | `intentional deviation` | `deprecate`.
- [ ] Run **`rg`** or scoped search for `BackendApiClient`, direct Qdrant/SQLite usage in Cockpit, to validate matrix claims; if unverified, mark cell as “assumption — verify in implementation PR”.
- [ ] **Deferred question from origin:** External consumers of Next vs backend — document finding in matrix notes or “Unknown — assumed internal only” until validated.

**Test / review scenarios**

- [ ] Every row has **exactly one** outcome column value and at least one **file path** or explicit “N/A — doc-only obligation”.
- [ ] Rows covering **retrieval boundary** and **DbReader fallback** match current `SYSTEM_CONTRACT.md` enforcement paragraph.

---

### Unit 3 — Operator runbook (`docs/ops/cockpit_operator_observability.md`)

**Deliverables**

- [ ] **Link-only table:** Columns: **Question** | **How (command or path)** | **Where to read result**. Minimum rows: API liveness; Cockpit aggregated health (backend and/or Next proxy as documented in Unit 1); extraction activity / mutex signal (e.g. `GET /api/cockpit/config` per current `cockpit_api.py` / `router_state`); `scripts/gpu_process_guard.sh --check`; RAG stability (`financial-engine_v2/scripts/evaluate_rag_stability.py` → `financial-engine_v2/reports/rag_stability/`); embed model / baseline (`reports/runtime_embedding_model.txt`, `reports/vector_baseline.json` per existing embedding docs).
- [ ] **Profile note:** `LOCAL_BACKEND_PROFILE=isolated` vs full/docker — what is expected to fail or be absent (Qdrant, embeddings, etc.) per `financial-engine_v2/CLAUDE.md` profile table; link `docs/entrypoints.md` for boot.
- [ ] **Dry-run criterion (R10):** Add a one-line “acceptance” stating an operator can complete the table using only this doc + targets (self-check during PR).

**Test / review scenarios**

- [ ] Every link target path exists at plan time or is explicitly “generated by script X after run”.
- [ ] `docs/ops/README.md` lists the new runbook.

---

### Unit 4 — STATE and handoff

- [ ] Update `docs/claude/STATE.md` docs-governance row to reference `21_cockpit_client_contract.md` and mark mismatch **closed** or **narrowed** with one sentence.
- [ ] If `docs/claude/current-state.md` lists the same gap, align in the same PR.

**Test / review scenarios**

- [ ] STATE wording matches what was actually delivered (no claim of “full API audit” if matrix has open assumptions).

---

## Sequencing

1. **Unit 1** (contract body + index + SYSTEM_CONTRACT pointer) — foundation for review.  
2. **Unit 2** (matrix) — depends on Unit 1 structure (anchor for matrix section).  
3. **Unit 3** (runbook) — can proceed in parallel with Unit 2 once health/config paths are stable in Unit 1.  
4. **Unit 4** — last, after Units 1–3 merge-ready.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Matrix drifts from code within weeks | Matrix points to **files**, not line numbers; PR template reminder when touching `cockpit_api.py` or `cockpit-ui/app/api/cockpit/` |
| Runbook paths wrong on Docker vs host | Profile column + link to `docs/entrypoints.md` and compose docs |
| Duplicating SYSTEM_CONTRACT | Addendum **links**; normative text stays in `SYSTEM_CONTRACT.md` |

---

## Verification (repo commands — post-implementation)

```bash
python -m ruff check financial-engine_v2/backend financial-engine_v2/cockpit scripts
pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q
```

Doc-only change: ruff/pytest only if adjacent code was touched; otherwise **peer review** is the gate.

---

## Deferred to implementation / follow-up

- Embedding summary into `GET /api/cockpit/health` (product — not required for this plan).  
- Any **deprecate** row that implies code removal: separate PR with API consumer check.

---

## Status

| Field | Value |
|-------|--------|
| status | active |
| last_updated | 2026-04-11 |
