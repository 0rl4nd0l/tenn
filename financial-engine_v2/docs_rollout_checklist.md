# Safe Rollout Checklist (Phased)

This checklist tracks phased rollout for ingestion reliability, operator safety, and resource workflow adoption.

## Phase 0: Baseline and Guardrails
- [ ] Capture baseline `git status --short` output.
- [ ] Capture baseline action defaults in `cockpit/core/actions.py`.
- [ ] Confirm help smoke checks:
  - [ ] `python3 scripts/resource_library_workflow.py --help`
  - [ ] `python3 scripts/asx_enrichment_sweep_action.py --help`
- [ ] Record rollback boundary commit IDs once commits are created.

Pass criteria:
- No behavior changes introduced in this phase.

## Phase 1: Stability Fixes
- [ ] ASX discovery loop does not early-abort on an empty annual batch.
- [ ] DB commit failure after source-doc move rolls file move back (best effort).
- [ ] Classification runs on deduped `process_document_ids`.
- [ ] Conservative request defaults aligned:
  - `request_delay_ms=700`
  - `request_jitter_ms=900`
  - `failure_backoff_ms=2500`

Validation:
- [ ] One-day low-volume ASX sweep smoke run completes without path mismatch.
- [ ] No orphan moved files after simulated DB commit failure path.

## Phase 2: Operator Control and Runtime Safety
- [ ] Cockpit blocks concurrent action launches while one job is active.
- [ ] "Kill Running Action" is available in Chat and Ops screens.
- [ ] Cancellation cleans up active job state after terminate/kill.

Validation:
- [ ] Start long-running action and cancel; verify non-stuck state.
- [ ] Attempt second action while first is running; verify blocked message.

## Phase 3: Ticker Universe and Pacing
- [ ] `full_history_ticker_sync.py` supports:
  - [ ] `--ticker-universe-file`
  - [ ] `--max-tickers`
  - [ ] `--ticker-delay-seconds`
  - [ ] `--ticker-delay-jitter-seconds`
- [ ] Progress logging includes per-ticker index.
- [ ] Invalid argument values fail with clear errors.

Validation:
- [ ] Mixed newline/comma/commented universe file parses deterministically and dedupes.
- [ ] Smoke run with `--max-tickers 3` completes and writes report settings.

## Phase 4: Resource Workflow Rollout (Heuristic First)
- [ ] `resource_library_workflow.py` ingestion defaults to heuristic mode.
- [ ] LLM mode is explicit opt-in via `--use-llm`.
- [ ] README and playbook match actual CLI behavior.

Validation:
- [ ] Local E2E with `.txt`/`.md`:
  - inbox -> candidates -> approved/rejected -> contexts
- [ ] PDF ingestion path validated where `pymupdf` is available.

## Phase 5: Playbook-Driven Additions (Planned)
- [ ] Evidence-object schema defined (financial/news/macro/citations).
- [ ] JSON-first report contract defined.
- [ ] Reviewer feedback artifact format defined.
- [ ] Citation and contradiction quality gates defined.

Validation:
- [ ] Schema-level tests.
- [ ] Gate evaluation tests using curated fixtures.
