# WTC USD M Canonical10 Baseline Rerun Record - 2026-05-05

## Status

Completed. Canonical10 passed on import-valid HEAD `5405802b0b7d`.

## Purpose

Run a cleared-GPU, frozen-HEAD canonical 10-document strict Docling baseline after the WTC USD M / US$M normalization fix and the import-valid backend model repair.

## Checkpoint

- WTC fix commit: `5a419a4` (`milestone(extraction): detect WTC USD million table units`)
- Fix commit status: ancestor of both the original frozen target and import-valid HEAD `5405802b0b7d`.
- Original frozen code HEAD for rerun: `944fd43e6a0ba14c5010fca41ad2b8250b68db38`
- Original frozen HEAD status: invalid as a canonical baseline anchor because backend import failed without tracked `financial-engine_v2/backend/app/models/companies.py`.
- Import-valid repair branch: `repair/canonical10-import-valid`
- Import-valid repair worktree: `/mnt/sdb2/home/l4nd0/tenn-canonical10-import`
- Import-valid committed HEAD: `5405802b0b7d`
- Repair summary: restored tracked `financial-engine_v2/backend/app/models/companies.py` and narrowed `.gitignore` from `models/` to `/models/`.
- Branch at scheduling time: `preserve/dirty-work-20260430T065748Z`
- Scheduling-time GPU guard: `scripts/gpu_process_guard.sh --check` exited `0` on 2026-05-05.

The frozen target was intentionally changed only after the original target was proven import-invalid and the repair commit was created. Do not use `944fd43e6a0ba14c5010fca41ad2b8250b68db38` as the baseline anchor. Treat `5405802b0b7d` as the import-valid canonical10-validated anchor for this run.

## Lane / Mode

- Primary lane: Evaluation
- Supporting lanes: Financial Truth, Provenance
- Execution mode: validation-only, frozen-HEAD, no source edits during the run
- Contested surfaces: none
- Collision rule: do not run from a live mutable worktree unless HEAD is proven frozen; prefer a detached or dedicated validation worktree.

## Preconditions

Run preconditions used immediately before execution:

```bash
test "$(git rev-parse --short=12 HEAD)" = "5405802b0b7d"
git status --short
scripts/gpu_process_guard.sh --check
curl -fsS --max-time 3 http://127.0.0.1:8002/health || true
```

Required interpretation:

- `git status --short` must show no extraction/eval/provenance source changes. The known unrelated `tenn_prompt_contracts_response_guidelines.zip` is not part of this rerun.
- GPU guard must exit `0`.
- If `:8002` is already healthy, verify it is the dedicated extraction runtime and not the shared `:8001` lane.
- Do not run Cockpit chat or other GPU work during the baseline.

## Command Shape

The successful run used a timestamped report directory and the canonical 10 document ids:

```bash
RUN_DIR="reports/wtc_usdm_canonical10_baseline_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$RUN_DIR"

EXTRACTION_LLAMACPP_URL=http://127.0.0.1:8002 \
LLAMACPP_URL=http://127.0.0.1:8001 \
OLLAMA_URL=http://127.0.0.1:11434 \
LLM_API_KEY="${LLM_API_KEY:-local-openai-key}" \
EXTRACT_MODEL=qwen2.5-14b-instruct \
EXTRACTION_SERVER_CTX_SIZE=16384 \
LLAMA_SERVER_MMAP=0 \
LLAMA_SERVER_BIN=/mnt/sdb2/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server \
financial-engine_v2/.venv/bin/python scripts/run_isolated_docling_control.py \
  --start-runtime \
  --stop-runtime \
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

The run passed. Harness acceptance reported:

- `acceptance_profile`: `canonical10`
- 10/10 documents completed
- 0 failed documents
- 24/24 metric checks correct
- 10/10 trust outcomes
- 10/10 context outcomes
- strict Docling execution
- actual method `docling_gpu` for every document
- no parser fallback
- no extraction-output cache hits
- no timeout
- isolated endpoint `http://127.0.0.1:8002` used for every document
- shared endpoint `http://127.0.0.1:8001` avoided
- prompt cache disabled in runtime provenance

## Artifacts

- `/mnt/sdb2/home/l4nd0/tenn-canonical10-import/reports/wtc_usdm_canonical10_baseline_20260505T050911Z/canonical10.json`
- `/mnt/sdb2/home/l4nd0/tenn-canonical10-import/reports/wtc_usdm_canonical10_baseline_20260505T050911Z/canonical10.md`
- `/mnt/sdb2/home/l4nd0/tenn-canonical10-import/reports/wtc_usdm_canonical10_baseline_20260505T050911Z/llama_extraction_8002.log`

## Post-Run State

- Extraction runtime stopped after the run; `:8002` health check returned connection refused.
- `scripts/gpu_process_guard.sh --check` exited `0`.
- Repair worktree was clean.
- No tracked files were changed by the run.
- The pinned worktree used an ignored `financial-engine_v2/data/asx` symlink to read external source PDFs.

## Notes

This run does not approve prompt changes, parser routing changes, fallback behavior, validation loosening, gold-label edits, or DB/Qdrant writes.

This confirms controlled 10-doc / 24-check accuracy only. Broader ASX production generalization, runtime throughput, concurrent extraction experiments, and production-wide reliability claims remain deferred. The next implementation lane should be real-gold corpus expansion, not extraction redesign.
