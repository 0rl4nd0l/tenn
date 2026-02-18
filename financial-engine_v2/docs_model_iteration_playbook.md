# Model Iteration + Training Playbook (Now, then M40 Upgrade)

This playbook is for your exact situation:
- **today**: slower/weaker local model performance,
- **later**: add NVIDIA M40 and increase model capacity,
- **goal**: make the system continuously improve in a controlled, repeatable way.

## 1) Core principle: separate "serving" from "learning"

Use two loops:

1. **Serving loop (always-on)**
   - ingest PDF -> extract text/chunks -> embed -> retrieve -> extract JSON -> store results.
   - this is your current production flow.

2. **Learning loop (batch/offline)**
   - evaluate outputs against gold truth,
   - identify bad fields/chunks,
   - improve prompt/model/chunking,
   - optionally fine-tune,
   - promote only if metrics improve.

Do not let the live model "self-modify" in production without an evaluation gate.

## 2) What to set up now (works on weak hardware)

### A. Keep a model registry in config
Track each run with:
- embed model
- extract model
- prompt version
- chunk size/overlap
- run id + date

You already persist `extractor_version`, `model_name`, and `prompt_hash` in extraction runs.
Use that as your first model registry.

### B. Build a gold dataset (small first)
Create a curated set of 50-200 PDFs (quarterly/half-year/annual + hard edge cases).
For each PDF, store expected JSON labels for key fields.

Start with the fields you already extract:
- period_type
- period_end
- financial metrics
- risk/guidance/material changes

### C. Add automated evaluation reports
After each candidate change (prompt/model), compute:
- field-level precision/recall/F1,
- null-rate,
- parse-failure rate,
- latency per document,
- cost/throughput.

Then promote only if score improves and latency remains acceptable.

### D. Add a human approval queue for "new knowledge"
For your "analyze a book PDF then ask me to commit" goal, use a two-stage flow:

1. **Candidate memory generation**
   - model produces: summary, key claims, tags, confidence, source quote spans.
2. **Human gate**
   - you approve/reject/edit candidates.
3. **Commit**
   - approved entries go to your knowledge base (vector + structured tables).

This gives you controlled learning instead of accidental hallucination accumulation.

## 3) M40-specific expectations and model choices

The M40 is usable, but be realistic:
- older architecture, no modern tensor-core speedups,
- you will usually want quantized models (4-bit/5-bit/8-bit) for responsiveness.

### Recommended starting model ladder (Ollama)

1. **Embeddings (keep stable first)**
   - `nomic-embed-text` (current default) is a good baseline.

2. **Extraction model candidates**
   - baseline: `llama3.1:8b`
   - try next: a stronger 7B-14B instruction model that is good at structured extraction (for example Qwen-family instruct variants available in Ollama).

3. **Promotion strategy**
   - only promote a new model if eval metrics beat baseline on your gold set.

Do not choose a model only by benchmark charts; choose by your extraction KPI.

## 4) Fine-tuning path (when to do it)

Fine-tuning is useful if, after prompt + retrieval tuning, you still see recurring extraction errors.

### Practical order
1. Prompt tuning
2. Chunk/retrieval tuning
3. Model swap A/B tests
4. Fine-tuning (LoRA) only if needed

### Fine-tune data format
For extraction, format supervised pairs like:
- **input**: schema prompt + document chunk/text
- **output**: exact target JSON

Keep a strict held-out test split; never train on evaluation set.

## 5) "Teach from PDFs/books" workflow blueprint

For each uploaded PDF:

1. Extract text and chunk.
2. Generate:
   - concise summary,
   - key takeaways,
   - entities/concepts,
   - confidence + citation spans.
3. Write candidates to `knowledge_candidates` storage.
4. Present review screen/CLI prompt:
   - approve/reject/edit.
5. On approval:
   - embed and store in vector DB,
   - optionally map to structured tables for downstream analytics.
6. Re-index and make retrievable.

This gives you "learning" with provenance and control.

## 6) Minimum governance so iteration stays reliable

Add these release gates for model/prompt changes:
- parse success >= 99%
- null-rate no worse than baseline + threshold
- key metric F1 improves by threshold
- latency p95 below threshold

If gates fail, reject promotion automatically.

## 7) Suggested 30-day rollout

### Week 1
- Build gold dataset + scoring script.
- Freeze current baseline metrics.

### Week 2
- Prompt iterations (`v1`, `v2`, `v3`) with fixed model.
- Choose best prompt by metrics.

### Week 3
- Model A/B tests on same prompt.
- Promote best quality/latency tradeoff.

### Week 4
- Add human approval queue for knowledge commits.
- Add release gates in CI for prompt/model changes.

---

If you want, the next step can be implementing a concrete "candidate memory + approval" schema and CLI in this repo so you can start approving book/PDF takeaways immediately.
