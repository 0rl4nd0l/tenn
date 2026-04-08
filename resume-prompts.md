# Resume Prompts — Apr 1 Sessions

Copy-paste the prompt into the resumed session.

---

## Session 1: Embedding/RAG Re-embed Pipeline
```bash
cd ~/tenn && claude --resume ca27b7f8-26c6-4a30-b668-ae6a66d21d44
```

### Resume prompt:
```
You were running a batch re-embed of all 12 ASX tickers into Qdrant after improving the chunking pipeline (boilerplate filtering, sentence-boundary snapping). The improvements were validated on BHP first — overall quality went from 2.5 → 2.8, with section value +0.3 and text quality +0.3.

You committed the chunking improvements, then kicked off the full re-embed batch. Progress when interrupted:
- BHP: done (60 docs, 3,747 points)
- CBA: done (203 docs embedded, 173 skipped — PDFs not on disk, 6,852 points)
- RIO: was in progress

The remaining tickers after RIO had not started yet. The full batch was expected to take ~30 min total.

Context on the broader system:
- Transcripts pipeline: verified, staging gate enforced (ingest_transcript.py → commentary_ingest.py → commentary_chunks Qdrant collection, staged_chunks review flow)
- Pass 3b narrative extraction exists but is limited (4 fields from 4,000 chars, section headers discarded during chunking)
- Non-financial announcements weren't hitting the pipeline

Please:
1. Check if the re-embed batch process is still running or died
2. If died, resume from where it left off (skip BHP and CBA, continue from RIO onward)
3. If completed, run the final quality eval comparison across all tickers
4. Report the before/after quality scores
```

---

## Session 2: PDF Financial Metric Extraction Eval
```bash
cd ~/tenn && claude --resume 03f06850-d97d-490c-96f0-6c1c701ed409
```

### Resume prompt:
```
You were running a live eval of the PDF financial metric extraction system using a new local LLM model. Current system state:

Baseline: ~89.5% extraction accuracy (excl. AZJ)
- Docling is the default PDF extraction backend (ML-based TableFormer for ASX filings)
- JSON sanitizer in llamacpp_runtime.py recovers garbled-font PDFs (AZJ: 0% → 81.8%)
- 15 eval fixtures total (13 original + 2 new: DXS/Dexus REIT, QBE insurance)

Research completed earlier in session (4 parallel agents):
1. ANZ banking regression (72.7%): root cause is prompts optimized for mining/industrial, not banking
2. AZJ pypdfium2: NOT worth pursuing — same garbled output, Identity-H font issue is at PDF level
3. Fixture expansion: added DXS (REIT) and QBE (insurance) to diversify beyond mining-heavy set
4. FX rates: recommended RBA as primary source, Yahoo Finance fallback, convert at query time not extraction time

The eval was running with:
- LLM_API_KEY=local-openai-key (fixes previous 401 auth error — server requires Bearer token via --api-key)
- EXTRACT_MODEL=gpt-oss-20b-mxfp4 (testing the new local model)
- pytest running 15 fixtures

When interrupted (~23 min in), the process was alive (2.2GB RAM, 6% CPU) doing CPU-bound docling PDF parsing. Output was buffered. Expected 10-20 more min.

Also noted: gpt-oss-20b-mxfp4 was installed as a GGUF but never wired into config or docs.

Please:
1. Check if the eval process is still running or completed
2. If died, re-run: LLM_API_KEY=local-openai-key EXTRACT_MODEL=gpt-oss-20b-mxfp4 pytest (the extraction eval)
3. Report accuracy results per fixture and overall vs the 89.5% baseline
4. If accuracy improved, document gpt-oss-20b-mxfp4 in the project config/docs
5. Address the ANZ banking prompt regression if time permits
```

---

## Session 3: llama.cpp Model Router Configuration
```bash
cd ~/tenn && claude --resume 8d1127ab-147a-4604-8a0b-1fec8e663a0b
```

### Resume prompt:
```
This session is likely COMPLETE. 425 tests passed and frontend was built. Verify and wrap up.

What was done:
- Configured llama.cpp --models-dir router mode for Tesla M40 (24GB VRAM)
- Used llmfit recommendations: Qwen3-30B-A3B-Instruct-2507-FP8 as the primary model (MoE: 30B params, ~3B active per token, ~15.6GB at Q4_K_M)
- Downloaded models, configured HybridRouter and cockpit client to use single-instance multi-model server on :8001
- Fixed cockpit_api.py / cockpit_service.py import issue (cockpit package not mounted in Docker container — made import conditional)
- Verified Anthropic fallback works (returns valid JSON from Claude)
- Fixed test mock to accept new `model` kwarg
- 425 tests passed, frontend built

Please:
1. Verify the commit landed (check git log for the most recent commit)
2. Confirm llama-server is running with --models-dir and the Qwen3 model is loadable
3. If everything checks out, just confirm session is complete — no further action needed
```
