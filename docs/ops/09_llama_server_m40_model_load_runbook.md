# 09 — llama-server on Tesla M40: model load stalls and fair extraction eval

**Host:** Tesla M40 (Maxwell, sm_52), 24 GB VRAM.  
**Scope:** `llama-server` from `tools/llama.cpp/build-cuda`, canonical chat/router port **8001**, optional extraction **8002**.  
**Launcher:** `scripts/run_llama_server.sh` (router or single-model). See also `scripts/run_extraction_server.sh` for port 8002.

Related: [openclaw_ops_loop.md](openclaw_ops_loop.md), [SYSTEM_CONTRACT.md](../architecture/SYSTEM_CONTRACT.md) (GPU process budget, ports 8001/8002), `scripts/gpu_process_guard.sh`.

---

## 1. Before you restart or spawn a server

1. Check topology and VRAM:  
   `bash scripts/gpu_process_guard.sh --check`  
   Exit **1** = unauthorised `llama-server` ports; **2** = VRAM critically low. Resolve before loading a large model.

2. Keep only **one** primary instance per port (contract: 8001 chat/router, 8002 extraction when used). Do not stack ad-hoc servers.

---

## 2. Symptoms (mmap / load path on M40)

| What you see | Likely meaning |
|----------------|----------------|
| `nvidia-smi` memory stays **~0.7–1 GiB** for many minutes while “loading” | Weights are not reaching GPU; load stuck early. |
| `curl` `/health` alternates **503** (`Loading model`) and **200** | Server process alive but load not finishing cleanly. |
| Process state **`Dl`** in `ps` (uninterruptible sleep) | Often disk/page-cache I/O in the mmap path while CUDA upload runs. |
| **Router** mode: `/models/load` or first chat **times out**, VRAM flat | Subprocess load can stall the same way as direct mode on this stack. |

Model file on **local ext4** (not NFS) still helps; if symptoms persist, treat as **llama.cpp build + Maxwell + mmap** interaction, not “bad GGUF path” alone.

---

## 3. First fix: disable mmap (supported by launcher)

`scripts/run_llama_server.sh` maps **`LLAMA_SERVER_MMAP=0`** → passes **`--no-mmap`** to `llama-server`.

Set in the shell **or** in the host override file (same keys as elsewhere in this repo; do not commit that file):

```bash
export LLAMA_SERVER_MMAP=0
# then start via your usual path, e.g.:
bash scripts/run_llama_server.sh
```

**Expect:** VRAM should climb into the **multi‑GB** range within a reasonable time (exact peak depends on model and `--n-gpu-layers`). If load completes, `/health` should stabilise on **200** and `/v1/models` should list the loaded model.

**Trade-off:** Slower startup and higher RAM pressure than mmap; acceptable when mmap path stalls.

---

## 4. Router vs single-model for debugging

- **Router** (`LLAMA_SERVER_ROUTER_MODE=1`, `--models-dir`, presets): convenient for switching models; if load **never** raises VRAM, reproduce in **single-model** mode to isolate router vs core load.
- **Single-model** (`LLAMA_SERVER_ROUTER_MODE=0`, `LLAMA_SERVER_MODEL=/path/to/model.gguf`): fewer moving parts for evals and bisecting regressions.

---

## 5. Fair extraction / baseline eval

1. **Fix the server first** (Section 3) so the **intended** GGUF is actually resident (confirm with `nvidia-smi` + `/v1/models`).
2. **Match the baseline model** (name and quant) to whatever `extraction_baseline.json` / the eval harness assumes. A run against a different model **invalidates** before/after accuracy comparisons.
3. If chat uses **8001** and extraction expects **instruct** on **8002**, use `scripts/run_extraction_server.sh` or a second `run_llama_server.sh` with `LLAMA_SERVER_PORT=8002` and the instruct GGUF. Both launchers honour **`LLAMA_SERVER_MMAP=0`** (passes **`--no-mmap`**) if **8002** stalls the same way as **8001**.

---

## 6. Quick verification

```bash
curl -sS -H "Authorization: Bearer ${LLM_API_KEY:-local-openai-key}" http://127.0.0.1:8001/health
curl -sS -H "Authorization: Bearer ${LLM_API_KEY:-local-openai-key}" http://127.0.0.1:8001/v1/models
```

Use **8002** instead of **8001** when checking the extraction instance.

---

## 7. If still stuck

- Confirm **one** `llama-server` per port; kill stragglers after guard check.
- Try a **smaller** GGUF to see if VRAM moves at all (rules out total OOM).
- Revisit **CUDA build** of `llama-server` vs driver; Maxwell-specific issues are covered in [02_ollama_m40_validation_and_mitigation.md](02_ollama_m40_validation_and_mitigation.md) (Ollama-focused but same GPU generation context).
