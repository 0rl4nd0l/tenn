# Autoresearch Capability Evaluation

**Investigated:** 2026-03-21
**Status:** Deferred — no implementation. Decision record and future plan only.
**Scope:** Dev-side experiment loop only. Not for production financial-agent self-modification.

---

## Executive Summary

Two repositories were inspected to determine whether an autonomous experiment loop capability should be added to this project:

- **karpathy/autoresearch** — GPU ML-training optimizer, tightly coupled to single-GPU PyTorch/GPT training. Not transferable without substantial rewrite.
- **davebcn87/pi-autoresearch** — Domain-agnostic experiment loop for any measurable optimization target, built as a plugin for the `pi` platform. The architecture is more transferable, but runtime coupling to `pi-ai`, `pi-coding-agent`, and `pi-tui` makes direct adoption unsuitable.

**Recommendation: Option C — Borrow patterns only; build a Tenn-native implementation later if needed.**

Neither repo is usable directly. The conceptual pattern (try → measure → keep/discard → log → repeat) is worth implementing natively when the project has sufficient evaluation infrastructure. The prerequisite is a stable eval harness with deterministic metrics, which does not yet exist for all candidate subsystems.

This capability is **deferred**. It should be revisited only when trigger conditions are met (see below).

---

## Repo Comparison

### karpathy/autoresearch

| Attribute | Value |
|-----------|-------|
| Language | Python |
| License | None stated |
| Stars | ~45,900 (Confirmed) |
| Last active | March 2026 (Confirmed) |
| Core purpose | Autonomous overnight optimization of GPT model training on a single GPU |
| Optimization target | `val_bpb` (validation bits per byte) — hardwired to training |
| Mutation surface | `train.py` — the agent edits this file directly |
| Fixed surface | `prepare.py` — data prep; never modified by agents |
| Evaluation budget | Fixed 5-minute training runs per experiment |
| Dependencies | PyTorch, `uv` package manager, single NVIDIA GPU |
| Architecture shape | 3-file system: `prepare.py`, `train.py`, `program.md` |
| State persistence | DATA_MISSING — log format not confirmed from available files |
| Safety model | None documented — agent mutates production code files |
| Platform coupling | Single-GPU PyTorch training; highly domain-specific |

**Fit assessment:** Poor. The mutation model (agent edits `train.py`) and evaluation metric (`val_bpb`) are inseparable from GPU model training. There is no abstraction layer. Reusing this for RAG parameter optimization, routing thresholds, or extraction quality would require a complete rewrite that produces something unrelated to the original repo. The conceptual loop structure is the only transferable part.

**Should NOT be used directly:** Confirmed. No abstraction, no safety model, no pluggability, no persistence contract.

---

### davebcn87/pi-autoresearch

| Attribute | Value |
|-----------|-------|
| Language | TypeScript |
| License | MIT (Confirmed) |
| Stars | ~2,500 (Confirmed) |
| Last active | March 2026 (Confirmed) |
| Core purpose | Domain-agnostic autonomous experiment loop, inspired by karpathy/autoresearch |
| Optimization target | Any measurable metric (latency, bundle size, Lighthouse score, ML metrics) |
| Loop command | `/autoresearch` — enters optimization mode |
| Session persistence | `autoresearch.jsonl` (append-only metric history), `autoresearch.md` (session objectives) |
| Backpressure checks | Optional `autoresearch.checks.sh` — runs tests/lint after each benchmark |
| Confidence scoring | Median Absolute Deviation after 3+ runs; green ≥2.0×, yellow 1.0–2.0×, red <1.0× |
| Architecture shape | Extension (infrastructure tools: `init_experiment`, `run_experiment`, `log_experiment`) + Skill (domain knowledge) |
| Platform coupling | `pi-ai`, `pi-coding-agent`, `pi-tui` (peer dependencies — not optional) |
| Mutation model | DATA_MISSING — how the skill proposes and applies experiment changes is not fully documented in available files |
| Safety model | Backpressure checks (optional); no explicit rollback documented |

**Fit assessment:** Moderate for patterns; poor for direct adoption. The architecture is well-designed and the extension/skill separation is directly analogous to the Claude Code plugin model used in this project. The persistence contract (`autoresearch.jsonl` + `autoresearch.md`) is clean and reusable as a pattern. However, peer dependency on `pi-ai`/`pi-coding-agent`/`pi-tui` means the codebase cannot be used standalone. This is a TypeScript extension for a specific platform that this project does not use.

**Should NOT be used directly:** Confirmed. Runtime coupling to the `pi` platform is incompatible with this project's Python/FastAPI/llama.cpp stack.

---

## Confirmed Differences

| Dimension | karpathy/autoresearch | pi-autoresearch |
|-----------|----------------------|-----------------|
| Domain specificity | GPU ML training only | Any measurable metric |
| Language | Python | TypeScript |
| Platform coupling | PyTorch + single GPU | `pi-ai` ecosystem |
| Persistence | DATA_MISSING | `autoresearch.jsonl` + `autoresearch.md` |
| Backpressure / safety checks | None documented | Optional `checks.sh` |
| Confidence scoring | None documented | MAD-based after 3+ runs |
| License | None stated | MIT |
| Abstraction level | None | Extension/Skill architecture |
| Reuse feasibility | Pattern only | Pattern + persistence model |

---

## Fit Assessment for This Project

### Development side (candidate use cases)

| Subsystem | Autoresearch Fit | Notes |
|-----------|-----------------|-------|
| Extraction quality | Moderate | Would need eval harness with precision/recall metrics first |
| Routing thresholds | Moderate | `model_routing.yaml` weights are already hand-tuned; optimization loop could help |
| Retrieval parameters (top_k, score cutoff) | Moderate | Requires stable RAG eval baseline |
| Latency/cost tradeoffs | High | Well-defined metrics; good candidate for offline optimization |
| Report generation consistency | Low-Moderate | Hard to define a single scalar metric |
| Benchmark/eval harness improvement | Low | Meta-level; risk of benchmark gaming |

### Financial-agent production path

**Not suitable** for production self-modification. The financial pipeline must remain deterministic and auditable. Autonomous mutation of prompts, routing weights, or extraction logic in the production path is explicitly prohibited (see safety boundaries below).

---

## Recommendation: Option C — Borrow Patterns Only

**Neither repo should be adopted or forked.** The value is in the conceptual pattern, not the code.

The pattern worth borrowing:

1. **Append-only experiment log** (`autoresearch.jsonl` equivalent) — flat JSONL file per optimization session recording: run ID, parameter delta, metric before, metric after, verdict (keep/discard), timestamp.
2. **Session objectives file** (`autoresearch.md` equivalent) — human-readable markdown tracking current hypothesis, prior results, and constraints.
3. **Backpressure gate** — run full validation gate set (`pytest` + ruff + smoke) before any experiment result is marked `keep`.
4. **Confidence scoring** — require N≥3 runs before accepting an improvement to filter noise from benchmark variance.
5. **Fixed experiment budget** — time-boxed or call-count-boxed evaluation windows to keep experiments comparable.
6. **Separation of fixed vs. mutable surfaces** — explicitly designate which config files / parameters are mutable per experiment session.

A Tenn-native implementation would be:
- Python, not TypeScript
- CLI-driven (not a platform extension)
- Integrated with existing validation gate set
- Explicitly scoped to one subsystem per session
- Log-first: every experiment is recorded before any change is applied

**Prerequisite that does not yet exist:** A stable, fast, deterministic eval harness covering each candidate subsystem. Without this, an experiment loop has no valid metric to optimize. This is the primary deferral reason.

---

## Safe Future Use Cases

These are allowed when implemented with proper guards (see Future Plan):

- **Offline routing threshold optimization** — run candidate `model_routing.yaml` weight sets against a frozen eval dataset; pick the set with best latency/accuracy tradeoff.
- **Retrieval parameter sweeps** — sweep `top_k`, score cutoffs, and chunk sizes against a canonical RAG eval baseline.
- **Extraction quality optimization** — vary prompt templates or extraction parameters against a labeled financial extraction test set.
- **Latency regression detection** — run before/after benchmarks when changing inference paths.

---

## Prohibited Use Cases

These must never be enabled, regardless of implementation maturity:

| Use Case | Prohibition Reason |
|----------|-------------------|
| Autonomous mutation of production prompts | Non-auditable; financial reasoning must be traceable |
| Self-modification of final investment reasoning behavior | Core safety constraint; violates auditability requirement |
| Autonomous schema / DB changes | Explicitly prohibited in CLAUDE.md |
| Autonomous benchmark redefinition | Benchmark gaming; invalidates eval history |
| Auto-apply of experiment results to production without human review | No human-in-the-loop review = not allowed |
| Optimization of the optimization loop itself | Meta-level; uncontrollable drift |
| Running experiment loops in production runtime | Development/shadow mode only |

---

## Confirmed / Inferred / Speculative

### Confirmed
- karpathy/autoresearch is hardwired to GPU PyTorch training; `val_bpb` is the only metric.
- karpathy/autoresearch has no stated license.
- pi-autoresearch is MIT licensed.
- pi-autoresearch requires `pi-ai`, `pi-coding-agent`, `pi-tui` as peer dependencies — these are not optional.
- pi-autoresearch uses `autoresearch.jsonl` (append-only) and `autoresearch.md` (session state) for persistence.
- pi-autoresearch implements optional backpressure checks via `autoresearch.checks.sh`.
- pi-autoresearch uses MAD-based confidence scoring after 3+ runs.
- This project's validation gate set is a 10-step sequence defined in `docs/validation_baseline.md`.
- The financial pipeline requires determinism and auditability per CLAUDE.md.

### Inferred
- pi-autoresearch's `/autoresearch` command and extension/skill architecture would map well to the Claude Code plugin/skill system used in this project.
- The backpressure check pattern in pi-autoresearch is directly analogous to this project's existing validation gate set.
- The primary deferral reason (no stable eval harness) is real — `docs/architecture/12_evaluation_and_drift_monitoring.md` exists but the gate set is not uniformly fast or deterministic for all candidate subsystems.
- karpathy/autoresearch `program.md` content is not available (404 during fetch); its exact agent instruction format is unknown.

### Speculative
- A Tenn-native implementation could be built in ~2–3 days of focused work once eval prerequisites are met.
- The routing threshold optimization use case is likely the highest-value entry point, given the existing `model_routing.yaml` weight structure.
- pi-autoresearch's mutation model may use the Claude API / `pi-coding-agent` to propose code changes, but this is not confirmed from available documentation.

---

## DATA_MISSING

- `karpathy/autoresearch/program.md` — baseline agent instructions file; fetch returned 404. Content unknown. This would clarify the agent instruction format and mutation constraints.
- `karpathy/autoresearch` — no license file present. Cannot confirm permissive usage.
- `pi-autoresearch` — how the skill proposes and applies experiment changes is not fully documented. The extension/skills directories were empty in the cloned repo, suggesting the actual implementation is user-provided or loaded separately.
- `pi-autoresearch` — whether the agent auto-applies changes or requires human approval is not confirmed.
- `docs/architecture/12_evaluation_and_drift_monitoring.md` — not read during this investigation. May contain eval infrastructure that affects the prerequisite assessment.

---

## Open Questions

1. Does `12_evaluation_and_drift_monitoring.md` already define a deterministic eval harness that could serve as the optimization target metric?
2. Is there an existing benchmark runner (e.g., in `scripts/`) that could be used as the "run experiment" step without new infrastructure?
3. Would the existing `reports/baselines/canonical_eval_baseline_latest.json` format serve as a frozen baseline for offline optimization sessions?

---

## Related Docs

- `docs/architecture/future_capabilities.md` — "Autonomous Dev Optimization Loop" section
- `docs/architecture/12_evaluation_and_drift_monitoring.md` — existing eval/drift infrastructure
- `docs/validation_baseline.md` — 10-step validation gate set
- `docs/architecture/model-routing.md` — routing weights (candidate optimization target)
