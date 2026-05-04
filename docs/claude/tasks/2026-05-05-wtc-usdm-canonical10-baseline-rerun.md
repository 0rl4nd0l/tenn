# WTC USD M Canonical10 Baseline Rerun Schedule - 2026-05-05

## Status

Scheduled, not started.

## Purpose

Run a cleared-GPU, frozen-HEAD canonical 10-document strict Docling baseline after the WTC USD M / US$M normalization fix.

## Checkpoint

- WTC fix commit: `5a419a4` (`milestone(extraction): detect WTC USD million table units`)
- Fix commit status: ancestor of scheduled frozen HEAD.
- Frozen code HEAD for rerun: `944fd43e6a0ba14c5010fca41ad2b8250b68db38`
- Branch at scheduling time: `preserve/dirty-work-20260430T065748Z`
- Scheduling-time GPU guard: `scripts/gpu_process_guard.sh --check` exited `0` on 2026-05-05.

Do not update the frozen code HEAD silently. The docs-only scheduling commit is not the runtime target. Run from a detached or dedicated validation worktree checked out at `944fd43e6a0ba14c5010fca41ad2b8250b68db38`; if `git rev-parse HEAD` differs from that value when the rerun is about to start, stop and report drift.

## Lane / Mode

- Primary lane: Evaluation
- Supporting lanes: Financial Truth, Provenance
- Execution mode for the future rerun: validation-only, frozen-HEAD, no source edits
- Contested surfaces: none
- Collision rule: do not run from a live mutable worktree unless HEAD is proven frozen; prefer a detached or dedicated validation worktree.

## Preconditions

Run only when all gates pass immediately before execution:

```bash
test "$(git rev-parse HEAD)" = "944fd43e6a0ba14c5010fca41ad2b8250b68db38"
git status --short
scripts/gpu_process_guard.sh --check
curl -fsS --max-time 3 http://127.0.0.1:8002/health || true
```

Required interpretation:

- `git status --short` must show no extraction/eval/provenance source changes. The known unrelated `tenn_prompt_contracts_response_guidelines.zip` is not part of this rerun.
- GPU guard must exit `0`.
- If `:8002` is already healthy, verify it is the dedicated extraction runtime and not the shared `:8001` lane.
- Do not run Cockpit chat or other GPU work during the baseline.

## Command

Use a timestamped report directory, for example:

```bash
RUN_DIR="reports/wtc_usdm_canonical10_baseline_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_DIR"

EXTRACTION_LLAMACPP_URL=http://127.0.0.1:8002 \
LLAMACPP_URL=http://127.0.0.1:8001 \
LLM_API_KEY="${LLM_API_KEY:-local-openai-key}" \
EXTRACT_MODEL=qwen2.5-14b-instruct \
EXTRACTION_SERVER_CTX_SIZE=16384 \
LLAMA_SERVER_MMAP=0 \
financial-engine_v2/.venv/bin/python scripts/run_isolated_docling_control.py \
  --start-runtime \
  --disable-prompt-cache \
  --startup-timeout-seconds 600 \
  --runtime-log "$RUN_DIR/llama_extraction_8002.log" \
  --results-json "$RUN_DIR/canonical10.json" \
  --report-path "$RUN_DIR/canonical10.md" \
  --capture-payload \
  --doc-id bhp_a_2021-06-30_difficult \
  --doc-id bhp_a_2025-06-30 \
  --doc-id eqr_q_2025-12-31 \
  --doc-id gre_q_2024-12-31 \
  --doc-id gre_q_2025-09-30 \
  --doc-id min_h_2025-12-31 \
  --doc-id qbe_h_2025-06-30 \
  --doc-id rio_a_2023-12-31 \
  --doc-id rio_a_2024-12-31 \
  --doc-id tls_h_2025-12-31
```

## Acceptance Gate

The run passes only if the harness reports `acceptance_profile=canonical10` and:

- 10/10 documents completed
- 0 failed documents
- 24/24 metric checks correct
- 10/10 trust outcomes
- 10/10 context outcomes
- strict Docling execution
- actual method is `docling_gpu` for every document
- no parser fallback
- no extraction-output cache hits
- no timeout
- isolated endpoint `http://127.0.0.1:8002` used for every document
- shared endpoint `http://127.0.0.1:8001` avoided
- prompt cache disabled in runtime provenance

## Expected Artifacts

- `$RUN_DIR/canonical10.json`
- `$RUN_DIR/canonical10.md`
- `$RUN_DIR/llama_extraction_8002.log`
- Optional follow-up summary in `reports/<run-dir>/performance_summary.md` if a repeat cell is run later.

## Notes

This schedule does not approve prompt changes, parser routing changes, fallback behavior, validation loosening, gold-label edits, or DB/Qdrant writes.
