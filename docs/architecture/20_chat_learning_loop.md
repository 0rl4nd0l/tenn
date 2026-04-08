# 20 — Chat Learning Loop

> Status: **Active** — Implemented 2026-04-08
> Scope: `financial-engine_v2/backend/app/services/` — quality scoring, preference updating, skill patching
> Related: [17_agentic_chat_architecture.md](17_agentic_chat_architecture.md) (future agent transformation)

---

## 1. Overview

The chat learning loop makes the `/chat` endpoint smarter over time by learning from session quality signals. It mirrors the PDF extraction learning loop pattern (Hermes-inspired) but is adapted for chat/RAG quality improvement.

**Two-path architecture:**
1. **Fast path (deterministic, every turn):** Compute composite quality metric → update `chat_preferences.json` with retrieval params + router hints
2. **Slow path (LLM review, periodic):** Review accumulated session transcripts → patch skill files (`chat_skill.md`, `tenn-learned.md`)

---

## 2. Architecture

### 2.1 Data Flow

```
User → /chat endpoint
  |
  v
[Retrieval Orchestrator: Rule 0 checks chat_preferences.json]
  → Learned top_k, commentary_weight applied
  |
  v
[Router Optimizer: Rule 0 checks chat_preferences.json]
  → Learned preferred_role applied per financial_task_type
  |
  v
[Chat response generated]
  |
  v
[Quality Scorer: compute composite metric]
  → retrieval_precision (avg chunk final_score)
  → model_confidence (from router)
  → session_coherence (1 - cosine_sim with prior query)
  |
  v
[Store quality_metrics in session_memory]
  |
  v
[Fast path: Preference Updater (periodic)]
  → Read quality turns from memory
  → Group by (task_type, params)
  → Update chat_preferences.json with best-performing combos
  |
  v
[Slow path: Skill Reviewer (manual trigger)]
  → Sample last 50 sessions
  → LLM analyzes patterns
  → Patch chat_skill.md or tenn-learned.md
  → Create rollback snapshots
```

### 2.2 Components

| Component | File | Responsibility |
|-----------|------|----------------|
| Preferences I/O | `chat_preferences.py` | Atomic load/save/snapshot/restore for learned preferences |
| Quality Scorer | `chat_quality_scorer.py` | Compute composite metric from retrieval/confidence/coherence |
| Preference Updater | `chat_preference_updater.py` | Convert quality turns → preferences with min sample thresholds |
| Skill Reviewer | `chat_skill_reviewer.py` | LLM-driven skill patching with rollback |
| Skill Files | `chat_skill.md`, `tenn-learned.md` | Qualitative patterns + machine-learned insights |
| Retrieval Rule 0 | `retrieval_orchestrator.py` | Read learned `top_k` and `commentary_weight` |
| Router Rule 0 | `router_optimizer.py` | Read learned `preferred_role` per financial_task_type |
| Integration | `routes/chat.py`, `session_memory.py` | Wire scorer into chat endpoint, store quality metrics |

---

## 3. Composite Quality Metric

The quality scorer computes a weighted combination of three signals:

```python
composite_metric = (
    w_retrieval * retrieval_precision +
    w_confidence * model_confidence +
    w_coherence * session_coherence
)
```

### 3.1 Retrieval Precision

**Definition:** Average `final_score` from chunks returned by retrieval orchestrator.

`final_score` is computed by `source_weighting.py` as:
```
final_score = relevance × credibility × recency_decay
```

- **Relevance:** Cosine similarity between query embedding and chunk embedding
- **Credibility:** Source weighting (ASX docs > news > commentary)
- **Recency:** Time-based decay factor

**Range:** [0.0, 1.0]

**Interpretation:**
- **High (>0.7):** Retrieved chunks are relevant, credible, and recent
- **Low (<0.4):** Poor retrieval quality — chunks may be off-topic, old, or low-credibility

### 3.2 Model Confidence

**Definition:** Router optimizer's confidence score for the selected model/role.

Derived from:
- Candidate score spread (if top candidate is much better than runner-up, confidence is high)
- Performance metrics (latency, throughput, error rate)
- Queue pressure

**Range:** [0.5, 0.99]

**Interpretation:**
- **High (>0.9):** Router is confident this is the right model for the task
- **Low (<0.7):** Fallback scenario, performance degraded, or GPU pressure

### 3.3 Session Coherence

**Definition:** `1 - cosine_similarity(current_query, previous_query)`

High cosine similarity between consecutive queries indicates the user is rephrasing the same question (poor coherence — the system didn't answer well the first time).

**Range:** [0.0, 1.0]

**Interpretation:**
- **High (>0.7):** New topic, natural conversation flow
- **Low (<0.3):** User rephrasing — signal of poor initial response quality

### 3.4 Default Weights

| Metric | Weight | Rationale |
|--------|--------|-----------|
| Retrieval precision | 0.40 | Most important — bad retrieval = bad answer |
| Model confidence | 0.35 | Router quality matters for response coherence |
| Session coherence | 0.25 | Detects user dissatisfaction via rephrasing |

**Sample count:** Minimum 10 turns before trusting learned preferences

**Future:** Optimize weights via Thompson sampling (multi-armed bandit).

---

## 4. Fast Path: Preference Learning

### 4.1 Trigger

Runs periodically (every N turns, or on-demand via admin endpoint).

### 4.2 Logic

1. **Read quality turns** from `session_memory` (filter by `composite_metric >= threshold`)
2. **Group by:**
   - `(financial_task_type, retrieval_params)` → top_k, commentary_weight
   - `(financial_task_type, router_role)` → preferred_role
3. **Compute avg_composite_metric** per group
4. **Select best-performing** params/role for each task type (min sample count = 10)
5. **Update `chat_preferences.json`** atomically with snapshot

### 4.3 Preference Schema

```json
{
  "schema_version": 1,
  "updated_at": "2026-04-08T12:00:00Z",
  "source_session_id": "session_abc123",
  "metric_weights": {
    "w_retrieval": 0.4,
    "w_confidence": 0.35,
    "w_coherence": 0.25,
    "sample_count": 50
  },
  "retrieval_preferences": {
    "rag_financial_synthesis": {
      "top_k": 12,
      "commentary_weight": 0.3,
      "avg_composite_metric": 0.88,
      "sample_count": 25
    }
  },
  "router_preferences": {
    "valuation_analysis": {
      "preferred_role": "deep_reasoning",
      "avg_composite_metric": 0.92,
      "sample_count": 15
    }
  }
}
```

### 4.4 Rollback Protection

Before updating `chat_preferences.json`:
1. Create snapshot: `chat_preferences.json.prev`
2. Write new preferences atomically (temp file + rename)
3. If regression detected, restore: `restore_snapshot()`

---

## 5. Rule 0: Learned Preference Application

### 5.1 Retrieval Orchestrator

**Location:** `retrieval_orchestrator.py:retrieve()`

**Logic:**
```python
prefs = load_preferences(_CHAT_PREFERENCES_PATH)
if prefs:
    task_pref = prefs["retrieval_preferences"].get("rag_financial_synthesis")
    if task_pref:
        top_k_chunks = task_pref["top_k"]  # Override hardcoded default
        commentary_weight = task_pref["commentary_weight"]
        # Scale top_k_commentary based on weight
        total_target = top_k_chunks / (1 - commentary_weight)
        top_k_commentary = int(total_target * commentary_weight)
```

**Effect:** Retrieval uses learned parameters instead of hardcoded defaults (8 chunks, 0.25 commentary weight).

### 5.2 Router Optimizer

**Location:** `router_optimizer.py:_preferred_role_name()`

**Logic:**
```python
if financial_task_type:
    prefs = load_preferences(_CHAT_PREFERENCES_PATH)
    if prefs:
        task_pref = prefs["router_preferences"].get(financial_task_type)
        if task_pref and task_pref["preferred_role"] in {"router", "reasoning", "deep_reasoning"}:
            return task_pref["preferred_role"]  # Override hardcoded logic
```

**Effect:** Router uses learned role preference (e.g., `deep_reasoning` for `valuation_analysis`) instead of hardcoded heuristics.

### 5.3 Fallback Behavior

- **Missing preferences:** Use hardcoded defaults (no error)
- **Malformed JSON:** Log warning, use hardcoded defaults
- **Invalid values:** Ignore invalid preference, use hardcoded logic

---

## 6. Slow Path: Skill Patching

### 6.1 Trigger

Manual invocation (not yet wired to cron or endpoint).

### 6.2 Logic

1. **Sample sessions** from `session_memory` (last 50 sessions, max 10k tokens)
2. **LLM analysis:**
   - Prompt: "Analyze chat quality patterns. Identify recurring issues, successful strategies, and systematic improvements."
   - Output: Markdown diff or patch for skill files
3. **Apply patch:**
   - Create rollback: `chat_skill.md.prev`, `tenn-learned.md.prev`
   - Write patched content atomically
4. **Validation:**
   - Check syntax (markdown lint)
   - Verify no corruption

### 6.3 Skill Files

| File | Purpose |
|------|---------|
| `chat_skill.md` | Human-written qualitative guidance (e.g., "Prefer deep_reasoning for multi-company comparisons") |
| `tenn-learned.md` | Machine-learned patterns from session review (e.g., "When retrieval_precision < 0.5, suggest narrower query") |

**Separation rationale:** Machine-learned patterns should not overwrite human guidance. `tenn-learned.md` is append-only or diff-patched.

---

## 7. Integration with Chat Endpoint

### 7.1 Modified Files

| File | Change |
|------|--------|
| `routes/chat.py` | Import `chat_quality_scorer`, call `score_turn()` in `_analysis_response()`, log composite metric |
| `session_memory.py` | Extend `_build_turn_payload()` with `quality_metrics` parameter |

### 7.2 Non-Blocking Design

- Quality scoring is **logging-only** — no errors thrown
- If scorer fails, chat response still completes
- Learned preferences are **optional overrides** — fallback to hardcoded defaults always works

---

## 8. Testing

### 8.1 Test Coverage

| Test Suite | File | Tests | Coverage |
|------------|------|-------|----------|
| Preferences I/O | `test_chat_preferences.py` | 6 | Load, save, snapshot, restore, malformed handling |
| Quality Scorer | `test_chat_quality_scorer.py` | 7 | Retrieval precision, coherence, composite metric |
| Preference Updater | `test_chat_preference_updater.py` | 4 | Group by params, min samples, accumulation |
| Integration | `test_chat_learning_integration.py` | 3 | Full cycle, rollback, skill patching |
| Retrieval Rule 0 | `test_retrieval_orchestrator_learning.py` | 3 | Learned params, fallback, malformed |
| Router Rule 0 | `test_router_optimizer_learning.py` | 4 | Learned role, fallback, invalid role, non-financial skip |

**Total: 27 tests passing**

### 8.2 Regression Protection

- Existing chat endpoint tests still pass (learning loop is non-blocking)
- Rule 0 tests verify fallback when preferences missing/malformed
- Integration tests verify rollback mechanism

---

## 9. Operational Considerations

### 9.1 Cold Start

- On first deployment, `chat_preferences.json` does not exist
- System uses hardcoded defaults until min sample count reached (10 turns)
- No degradation during cold start

### 9.2 Preference Drift

- Preferences accumulate evidence over time (weighted averaging)
- Old evidence decays as new samples arrive
- Monitor `avg_composite_metric` for regression — if learned preference performs worse than baseline, rollback

### 9.3 Manual Override

- Operators can edit `chat_preferences.json` directly
- Snapshot/rollback mechanism protects against bad manual edits

### 9.4 Monitoring

**Key metrics to track:**
- `composite_metric` distribution over time (should trend upward)
- Learned preference adoption rate (% of requests using learned params)
- Rollback frequency (should be low)
- Skill patch success rate

---

## 10. Future Enhancements

### 10.1 Thompson Sampling for Weights

Replace fixed weights (0.4, 0.35, 0.25) with adaptive weights optimized via multi-armed bandit.

**Approach:**
- Each weight configuration is an "arm"
- Sample arms according to posterior probability of being optimal
- Update priors based on observed composite metric outcomes

### 10.2 Cross-Session Learning

Aggregate quality signals across users for global improvements (privacy-preserving).

### 10.3 Task Type Expansion

Current implementation focuses on `rag_financial_synthesis`. Expand to:
- `valuation_analysis`
- `peer_comparison`
- `earnings_analysis`
- `filing_summary`
- etc.

### 10.4 Automated Slow Path

Wire skill reviewer to:
- Cron job (weekly review)
- Admin endpoint (`POST /admin/review-chat-skills`)
- Auto-trigger when composite metric drops below threshold

### 10.5 A/B Testing Framework

Test learned preferences against hardcoded defaults with controlled experiments.

---

## 11. Contract Compliance

### 11.1 SYSTEM_CONTRACT.md

- ✅ No RAG logic in cockpit (all via backend APIs)
- ✅ No direct Postgres/Qdrant access from learning loop
- ✅ Deterministic preference storage (JSON atomic writes)
- ✅ Fast path is non-blocking (logs only, no errors thrown)
- ✅ Backend owns all retrieval logic (Rule 0 reads backend-generated preferences)

### 11.2 Engineering Discipline

- ✅ All changes tested with regression suite (27 tests)
- ✅ Milestone commits with `Working:` / `Tested:` fields
- ✅ No silent fallbacks (preference loading failures are logged)
- ✅ Snapshot/rollback for regression protection

---

## 12. Related Documentation

- **[17_agentic_chat_architecture.md](17_agentic_chat_architecture.md):** Future transformation to tool-calling agent
- **[18_cockpit_memory.md](18_cockpit_memory.md):** Session memory system (OpenViking) used by learning loop
- **[model-routing.md](model-routing.md):** Router optimizer (Rule 0 integration point)
- **PDF extraction learning loop:** `docs/superpowers/specs/2026-04-08-pdf-extraction-learning-loop-design.md` (pattern this mirrors)

---

## 13. Summary

The chat learning loop provides:
- **Deterministic quality measurement** via composite metric
- **Automatic parameter tuning** via fast path (retrieval params, router roles)
- **Qualitative skill accumulation** via slow path (LLM review → skill patches)
- **Regression protection** via snapshot/rollback
- **Non-breaking integration** (fallback to hardcoded defaults always works)

**Production status:** Active as of 2026-04-08. Will begin accumulating quality signals as `/chat` traffic flows.
