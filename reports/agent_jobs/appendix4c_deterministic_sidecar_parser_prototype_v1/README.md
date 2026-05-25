# Appendix 4C deterministic sidecar parser prototype v1

Issue: #57
Lane: Financial Truth
Mode: AUDIT ONLY / report-local design
Branch: `audit/repo-hygiene-safe-audits-v1-20260525`
HEAD at report write: `17a0226c47c62f873bb920edd9b9ac5a377cbcbb`
Task card: `docs/agent_tasks/appendix4c_deterministic_sidecar_parser_prototype_v1.md`

## Decision

Close #57 only as `COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS`.

The acceptance criteria are satisfied for the audit/design layer: Appendix 4C scope is bounded, deterministic assumptions are documented, no production wiring is changed, and explicit fixture/gate promotion criteria are written. Product remediation did not land, and no Appendix 4C parser was implemented in this pass.

The safe next step is a child task: `[Financial Truth] Appendix 4C candidate sidecar parser v1`.

## Contract preflight

Target system layer: report-local Evaluation / Financial Truth evidence artifacts. This pass does not execute or alter the ingestion, extraction, storage, retrieval, analysis, or client runtime path.

Relevant contract rules:

- Backend remains the authority for extraction and canonical financial truth.
- Pipeline layering stays intact: ingestion, extraction, storage, retrieval, analysis, client.
- Metric extraction must use explicit values only; no inference or substitution.
- The only currently allowed derivation is Appendix 5B capex from explicit sub-items, which this task does not extend.

What must not change:

- Production parser routing, Docling config, extraction prompts, canonical truth, source PDFs, DB/Qdrant/news/memory stores, production data, runtime/model/service config, and gold labels.
- Appendix 4C cash-flow rows must not become revenue, NPAT, net debt, or income-statement claims.

Why this change is safe: only the task card and report artifacts are written. The proposed parser remains a future child task with `canonical_write=false`, report-local output, and explicit promotion gates.

GPU process check: not required. This task does not spawn, restart, or depend on `llama-server`.

## Confirmed

- #57 is open and requests `appendix4c_deterministic_sidecar_parser_prototype_v1` with a task card, README, status, readiness map, fixture/gate proposal, and child task recommendation.
- The task card validates and allows only the card plus report artifacts under this report directory.
- The registry reported no active jobs before claim, and check-overlap passed for this task card.
- The repo has a synthetic Appendix 4C document-type fixture with `Appendix 4C`, `Quarterly cash flow report`, and `Rule 4.7B` anchors, negative Appendix 5B/annual/report anchors, explicit forbidden revenue/NPAT/net-debt inference, and `canonical_write=false`.
- The document-type fixture contract says Appendix 4C fixtures must not imply revenue, NPAT, net debt, or income-statement extraction, and it requires `canonical_write=false`.
- The comparator artifact schema is report-only, requires artifact-level and candidate-level `canonical_write=false`, forbids canonical writes, and says future parser prototypes must emit only caller-owned report paths.
- Comparator schema tests reject revenue, NPAT, and net debt as Appendix 4C candidate metrics.
- The current Appendix 5B deterministic parser is a candidate-only table-row parser pattern that does not write canonical truth or call LLM/runtime services.
- Current repo file inventory found no dedicated Appendix 4C parser module.

## Inferred

- A safe Appendix 4C implementation should be a separate candidate-only sidecar parser, not an extension of production parser routing.
- The Appendix 5B parser is a useful design pattern for table-row parsing, evidence capture, column role handling, and `DATA_MISSING`, but it cannot be treated as Appendix 4C support.
- Appendix 4C should remain report-local until a real table fixture corpus, forbidden-metric tests, no-routing checks, and no-regression gates exist.

## Speculative

- Candidate line items likely include current-quarter receipts from customers, net operating cash flow, net investing cash flow, net financing cash flow, and cash at end of period. Exact Appendix 4C line preferences, especially cash-end preference, still need real fixture verification.

## DATA_MISSING

- No dedicated Appendix 4C deterministic parser module was found.
- No real Appendix 4C structured table fixture corpus was validated in this task.
- Exact Appendix 4C line-item mapping still needs source-bound confirmation.
- Focused pytest/pnpm validation was not run because `pytest` and `pnpm` are unavailable from PATH in this worktree.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` are absent in this worktree.

## Parser readiness

See `parser_readiness_map.json`.

Summary:

- Ready: document-type metadata fixture and comparator artifact schema boundaries.
- Ready at schema-test level: forbidden Appendix 4C revenue/NPAT/net-debt candidates.
- Pattern only: Appendix 5B deterministic parser.
- Missing: dedicated Appendix 4C parser, real table fixture corpus, exact line-item proof.
- Forbidden in this task: production routing and canonical writes.

## Fixture and gate proposal

See `fixture_gate_proposal.json`.

Minimum future gates:

- Appendix 4C identity anchors pass and conflicting document-type anchors abstain.
- Current-quarter and year-to-date values are not conflated.
- Missing lines/columns produce `DATA_MISSING`, never zero.
- Revenue, NPAT, net debt, EPS, margins, segment metrics, and income-statement/balance-sheet blocks remain forbidden.
- Candidate artifacts remain `canonical_write=false`.
- No production parser routing imports the sidecar output.
- No DB, Qdrant, news, memory, source PDF, prompt, gold-label, model, runtime, or service config writes occur.

## Next child task

Title: `[Financial Truth] Appendix 4C candidate sidecar parser v1`

Scope:

- Add an isolated candidate-only Appendix 4C parser and tests/fixtures if registry and allowed-file checks are clean.
- Input must be already-extracted table rows.
- Output must be report-local comparator artifacts with `canonical_write=false`.
- Keep it unwired from production parser routing and canonical writes.

## Closeout classification

Reviewer classification: `AUDIT_ONLY_NO_REMEDIATION`, `NEEDS_FOLLOWUP`.

Closeout gate: `COMPLETED_AUDIT_ONLY_WITH_FOLLOWUPS`, assuming the child issue is created before #57 is closed.

This issue must not be described as product-remediated.
