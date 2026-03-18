<analysis>
Here is my detailed review of the current codebase, using repository artifacts as proxy inputs because the provided placeholders (`IMPLEMENTATION_PLAN`, `TECHNICAL_SPECIFICATION`, `PROJECT_REQUEST`, `PROJECT_RULES`, `EXISTING_CODE`) were not populated in the prompt.

1. Code Organization & Structure
- The repo is clearly split between runtime engine (`financial-engine_v2/backend`), terminal UX (`financial-engine_v2/cockpit`), and operational scripts (`financial-engine_v2/scripts` plus root `scripts`). This matches the local-first ingestion objective and phased execution workflow documented in `README.md`, `docs/phase_checklist.md`, and `STATE.md`.
- Several core modules are very large and carry mixed responsibilities. `cockpit/ui/app.py` combines app wiring, runtime orchestration, UI state, long-running job control, and feature-flag bootstrapping in a single file; this raises change risk and makes focused testing harder.
- API route code in `backend/app/api/routes.py` is minimal and functional, but packs business logic/serialization inline and uses compressed one-line function style. This reduces readability and makes behavior changes harder to review safely.
- Extraction/pipeline logic in `backend/app/services/pipeline.py` has strong functional breadth but shows signs of utility sprawl (`coerce`, URL normalization, filename slugging, failure taxonomy, HTTP handling) all in one module.

2. Code Quality & Best Practices
- Positive: there are explicit defaults for local isolated mode and clear runbook commands; this helps reproducibility and ops handoff.
- Gaps:
  - Inconsistent style/readability in backend endpoints (`routes.py`) and extraction helpers (`extraction.py`)—compressed statements and limited docstrings make maintenance slower.
  - Error classification in `pipeline.py` is keyword-based and practical, but not centrally typed; adding new failure classes requires editing broad logic rather than a focused taxonomy module.
  - Prompt/version traceability is present (`EXTRACTOR_VERSION`), but `prompt_hash` behavior documented in README indicates versioning is still coarse; this can weaken regression attribution when prompt details change.
  - Config handling in `cockpit/core/config.py` is good baseline, yet validation is partial (e.g., some env overrides validated, others not), which can allow silent misconfiguration.

3. UI/UX (Cockpit TUI)
- Positive: strong operational affordances (quick action buttons, kill action, mode toggles) and sensible keybindings.
- Gaps:
  - Chat input placeholder is overloaded and difficult to scan; command discoverability can be improved through compact help surfaces.
  - Operations and chat surfaces duplicate action-launch controls; this risks drift and increases user confusion if behavior diverges.
  - The app CSS and widgets are embedded in `app.py`, making UI refinement and consistency auditing harder.
  - User feedback and error states are mostly log-line driven; lightweight structured status chips/messages could improve action confidence and reduce operator errors.

4. Data Extraction Quality (including Docking/Docling vs `pdftotext`)
- Current extraction paths are split:
  - Backend ingestion/extraction pipeline (`backend/app/services/text_extract.py`) uses PyMuPDF (`fitz`) plain text extraction.
  - Metric-oriented root scripts (`scripts/extract_financial_metrics.py`) use `pdftotext -layout` and `pdftotext -bbox-layout` for geometry-aware parsing.
- No Docling/Docking implementation was found in the codebase; therefore a true Docking-vs-`pdftotext` runtime A/B comparison is currently not possible without adding a new extractor adapter first.
- Accuracy determination from available evidence:
  - Parser/financial tooling tests are strong and currently passing (`scripts/test_pdf_financial_tools.py`, `scripts/test_ocr_last_resort.py`), which supports parser consistency and OCR fallback behavior.
  - However, there are no in-repo sample PDFs to execute a direct corpus-level extraction fidelity benchmark in this environment.
  - Conclusion: extraction logic appears structurally sound and test-validated for parsing behaviors, but end-to-end text fidelity accuracy remains only partially verified until a shared PDF benchmark set is run across extractor backends.
</analysis>

# Optimization Plan

## Code Structure & Organization
- [ ] Step 1: Decompose Cockpit App Composition and Runtime Wiring
  - **Task**: Split `cockpit/ui/app.py` into focused modules: UI composition/layout, dependency bootstrap, and job/chat orchestration adapters while preserving public behavior.
  - **Files**:
    - `financial-engine_v2/cockpit/ui/app.py`: keep only top-level `CockpitApp` shell and delegated calls.
    - `financial-engine_v2/cockpit/ui/layout.py` (new): move CSS/layout composition and screen registration helpers.
    - `financial-engine_v2/cockpit/ui/runtime.py` (new): move service/client bootstrap and runtime flag initialization.
    - `financial-engine_v2/cockpit/ui/job_state.py` (new): isolate active job/chat state transitions and guard helpers.
  - **Step Dependencies**: None.
  - **User Instructions**: Run cockpit smoke (`python -m cockpit.main`) and verify hotkeys + action execution still work.
  - **Success Criteria**:
    - No behavior regression in startup and key navigation.
    - `app.py` reduced to orchestration shell with clearer responsibility boundaries.

- [ ] Step 2: Introduce API Response Serializer Layer
  - **Task**: Extract response shaping from `routes.py` into serializer helpers to simplify endpoint functions and enforce consistent payload structures.
  - **Files**:
    - `financial-engine_v2/backend/app/api/routes.py`: keep route parsing + service calls only.
    - `financial-engine_v2/backend/app/api/serializers.py` (new): add `document_to_api`, `financial_to_api`, `risk_to_api` helpers.
    - `financial-engine_v2/scripts/test_import_smoke_runtime.py` (or nearest API smoke test): add import/reference check for serializer module.
  - **Step Dependencies**: Step 1 independent.
  - **User Instructions**: Hit `/api/docs`, `/api/financials`, `/api/risk` to confirm unchanged shape.
  - **Success Criteria**:
    - Route methods are short and readable.
    - Existing API contract remains backward-compatible.

## Code Quality & Best Practices
- [ ] Step 3: Extract and Type Failure Taxonomy + Normalization Utilities
  - **Task**: Move extraction failure taxonomy and normalization helpers from `pipeline.py` into a dedicated utility module with typed interfaces.
  - **Files**:
    - `financial-engine_v2/backend/app/services/pipeline.py`: replace inline helpers with imports.
    - `financial-engine_v2/backend/app/services/failure_taxonomy.py` (new): taxonomy constants + classifier.
    - `financial-engine_v2/backend/app/services/normalize.py` (new): URL/text/float coercion helpers.
    - `financial-engine_v2/scripts/test_pipeline_service_extraction_accounting.py`: extend assertions to cover new module pathways.
  - **Step Dependencies**: None.
  - **User Instructions**: Run targeted tests for extraction accounting and one sync ticker backfill dry run.
  - **Success Criteria**:
    - Classifier behavior parity retained.
    - Pipeline module complexity reduced without changing output semantics.

- [ ] Step 4: Strengthen Prompt Versioning and Extraction Traceability
  - **Task**: Promote extraction prompt/version metadata from fixed literals to explicit versioned constants and persisted run metadata to improve reproducibility.
  - **Files**:
    - `financial-engine_v2/backend/app/services/extraction.py`: add explicit prompt-template version ID + deterministic hash helper.
    - `financial-engine_v2/backend/app/services/pipeline.py`: persist hash/version fields from extraction helper.
    - `financial-engine_v2/scripts/test_analysis_report_schema.py` (or extraction-facing tests): validate metadata presence in runs.
    - `financial-engine_v2/README.md`: document updated traceability behavior.
  - **Step Dependencies**: Step 3 recommended (shared normalization/helpers).
  - **User Instructions**: Re-run one extraction and inspect stored extraction run metadata.
  - **Success Criteria**:
    - Prompt changes become auditable across runs.
    - No impact on existing extraction JSON schema.

- [ ] Step 5: Add Config Validation Pass for Critical Runtime Inputs
  - **Task**: Add explicit post-load config validation to fail fast on invalid URLs, unsupported modes, and malformed thresholds.
  - **Files**:
    - `financial-engine_v2/cockpit/core/config.py`: add `validate_config(cfg)` and call from load/apply path.
    - `financial-engine_v2/scripts/test_cockpit_status_normalization.py` or a dedicated config test file: add negative/positive validation tests.
    - `financial-engine_v2/config/cockpit.yaml`: add comments/examples for validated fields.
  - **Step Dependencies**: None.
  - **User Instructions**: Start cockpit with intentionally invalid env var and confirm clear startup error.
  - **Success Criteria**:
    - Misconfiguration fails with actionable messages.
    - Valid current configs continue to boot unchanged.

## Data Extraction Quality & Accuracy Validation
- [ ] Step 6: Add Unified Extractor Adapter Interface (PyMuPDF, `pdftotext`, optional Docling)
  - **Task**: Create a common extraction adapter so the same input PDFs can be run through multiple backends with normalized outputs for quality comparison.
  - **Files**:
    - `financial-engine_v2/backend/app/services/text_extract.py`: refactor into strategy-based adapter entrypoint.
    - `financial-engine_v2/backend/app/services/text_extract_adapters.py` (new): implement `pymupdf` and `pdftotext` adapters; define optional `docling` adapter stub if dependency not installed.
    - `financial-engine_v2/backend/app/core/config.py`: add extractor backend selection env/config (`TEXT_EXTRACT_BACKEND`).
    - `financial-engine_v2/scripts/test_import_smoke_runtime.py`: smoke imports for new adapter module.
  - **Step Dependencies**: Step 3 recommended.
  - **User Instructions**: Set `TEXT_EXTRACT_BACKEND=pymupdf|pdftotext` and verify ingestion still completes.
  - **Success Criteria**:
    - Backend can switch extractor without touching business logic.
    - Fail-closed behavior when optional adapter (Docling) is unavailable.

- [ ] Step 7: Build Extraction Benchmark Harness and Accuracy Scorecard
  - **Task**: Add a repeatable script that runs the same PDF set through each extractor and scores text fidelity + metric capture deltas.
  - **Files**:
    - `scripts/benchmark_extraction_backends.py` (new): run A/B comparisons and emit JSON/Markdown scorecards.
    - `scripts/test_benchmark_extraction_backends.py` (new): unit tests for scoring math and report generation.
    - `docs/canonical_datasets.md`: document benchmark dataset contract and expected folder layout.
  - **Step Dependencies**: Step 6 required.
  - **User Instructions**: Provide a local PDF fixture set and run benchmark script with `--backends pymupdf,pdftotext[,docling]`.
  - **Success Criteria**:
    - Scorecard includes per-PDF text coverage, numeric metric agreement, and extraction error classes.
    - Produces deterministic outputs for CI/local regression checks.

- [ ] Step 8: Determine and Enforce Accuracy Gate for Production Extraction
  - **Task**: Define threshold-based acceptance criteria (e.g., metric agreement %, null-rate ceiling, OCR fallback rate) and enforce in validation scripts.
  - **Files**:
    - `scripts/validation_gates.py`: add extractor accuracy gate checks.
    - `scripts/test_validation_gates.py`: add passing/failing benchmark fixture cases.
    - `runbook.md`: add explicit “Extractor Accuracy Gate” command sequence.
  - **Step Dependencies**: Step 7 required.
  - **User Instructions**: Run validation gates after benchmark; only promote backend change if thresholds pass.
  - **Success Criteria**:
    - Backend/extractor changes cannot ship without meeting accuracy minimums.
    - Gate output is explicit and operator-readable.

## UI/UX Improvements
- [ ] Step 9: Improve Chat Command Discoverability and Reduce Placeholder Overload
  - **Task**: Replace long input placeholder with concise hint + dedicated in-app command reference panel/toggle.
  - **Files**:
    - `financial-engine_v2/cockpit/ui/screens.py`: adjust input placeholder and add `Help` button/modal.
    - `financial-engine_v2/cockpit/ui/app.py` (or new UI helper file from Step 1): wire help action and keybinding.
  - **Step Dependencies**: Step 1 preferred.
  - **User Instructions**: Open chat and verify help surface includes all current slash commands.
  - **Success Criteria**:
    - Input line stays readable at normal terminal widths.
    - Operators can discover commands without memorizing placeholder text.

- [ ] Step 10: Unify Action Launch UX Between Chat and Operations Screens
  - **Task**: Create a shared action-launch component/helper used by both screens to avoid duplicated button/argument behaviors.
  - **Files**:
    - `financial-engine_v2/cockpit/ui/screens.py`: refactor duplicate action execution branches to shared helper.
    - `financial-engine_v2/cockpit/core/actions.py`: expose consistent metadata needed by both views.
  - **Step Dependencies**: Step 6 optional.
  - **User Instructions**: Trigger same action from both screens and verify equivalent argument parsing/log output.
  - **Success Criteria**:
    - Reduced duplicate logic.
    - Parity of behavior across navigation contexts.

- [ ] Step 11: Add Structured Runtime Status Messages for Action Lifecycle
  - **Task**: Add compact status indicators for queued/running/cancelled/completed/failed states in addition to log lines.
  - **Files**:
    - `financial-engine_v2/cockpit/ui/screens.py`: add status widgets in chat + operations.
    - `financial-engine_v2/cockpit/ui/app.py` (or `job_state.py` from Step 1): publish normalized lifecycle events.
    - `financial-engine_v2/scripts/test_cockpit_action_runtime_guards.py`: validate state transitions and conflict handling.
  - **Step Dependencies**: Step 1 and Step 7 recommended.
  - **User Instructions**: Run long job, cancel it, and confirm each state transition appears clearly.
  - **Success Criteria**:
    - Operators can determine current action state at a glance.
    - Cancellation and failure states are explicitly surfaced, not only log-text implicit.

## Logical Next Step
- [ ] Execute Step 1 and Step 2 first as a low-risk readability foundation, then implement Steps 3–8 (quality + extractor-accuracy hardening), and finish with Steps 9–11 (UX refinements) once behavior parity is confirmed.
