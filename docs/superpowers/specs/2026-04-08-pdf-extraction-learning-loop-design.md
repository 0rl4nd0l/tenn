# PDF Extraction Learning Loop

**Date:** 2026-04-08
**Status:** Draft
**Inspired by:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) learning loop architecture

## Summary

A closed-loop system that makes PDF extraction routing smarter over time. Two mechanisms work together:

1. **Fast path (deterministic):** After every pipeline run, extraction accuracy metrics per document type and method are written to a routing preferences file. The extraction router reads this on next run to make better method selections.

2. **Slow path (LLM review):** Every N runs (configurable, default 5), a background review agent reads accumulated evaluation reports and patches a qualitative extraction skill file — capturing insights metrics can't express.

Both paths are protected by the existing regression guard with automatic rollback on degradation.

## Motivation

Tenn's extraction pipeline already produces rich evaluation data (accuracy, completeness, fallback rates, stratified by document type and method) via `services/evaluation/scorer.py` and `services/orchestrator/pipeline_orchestrator.py`. However, this data is logged and forgotten. The extraction router (`services/extraction/router.py`) uses hardcoded thresholds that never adapt.

The Hermes Agent project demonstrates a practical pattern: background review agents that read execution history and create/patch skill files. This design adapts that pattern to Tenn's extraction pipeline, leveraging existing infrastructure (regression guard, evaluation scorer, pipeline orchestrator) rather than introducing new dependencies.

## Architecture

### Data Flow

```
Pipeline Run
    |
    v
evaluation_agent() -> eval report (stratified metrics)
    |
    +---> [Fast Path] preference_updater.py
    |         |
    |         v
    |     routing_preferences.json (method preferences per doc type)
    |
    +---> [Slow Path, every N runs] skill_reviewer.py
    |         |
    |         v
    |     extraction_skill.md (qualitative patterns)
    |
    v
Next Pipeline Run
    |
    v
router.py reads preferences + skill -> better method selection
    |
    v
regression_guard.py validates -> PASS: confirm | FAIL: rollback
```

### Integration Points

| Existing System | Integration | Change Type |
|---|---|---|
| `services/extraction/router.py` | Add Rule 0: learned preference lookup before hardcoded rules | Modified |
| `services/orchestrator/pipeline_orchestrator.py` | Call preference_updater after eval, trigger review agent every N runs | Modified |
| `autodev/runtime/regression_guard.py` | No changes — used as-is for validation | Unchanged |
| `services/evaluation/scorer.py` | No changes — output format already sufficient | Unchanged |

## Detailed Design

### 1. Fast Path: Deterministic Routing Updates

#### New File: `services/extraction/routing_preferences.json`

```json
{
  "schema_version": 1,
  "updated_at": "2026-04-08T14:30:00Z",
  "source_run_id": "run-123",
  "method_preferences": {
    "structured_financial_reports": {
      "preferred": "financial_metrics_pdftotext",
      "accuracy": 0.91,
      "fallback": "financial_metrics_docling",
      "fallback_accuracy": 0.78,
      "sample_count": 24,
      "last_updated": "2026-04-08T14:30:00Z"
    },
    "semi_structured_presentations": {
      "preferred": "financial_metrics_docling",
      "accuracy": 0.85,
      "fallback": "financial_metrics_pdftotext",
      "fallback_accuracy": 0.62,
      "sample_count": 18,
      "last_updated": "2026-04-07T09:15:00Z"
    }
  },
  "min_sample_count": 5
}
```

#### New Module: `services/extraction/preference_updater.py`

```python
def update_preferences(
    eval_report: dict,
    current_prefs: dict | None,
    min_sample_count: int = 5,
) -> dict:
    """
    Reads stratified accuracy from eval_report["stratified"]["document_type"],
    compares method accuracy per doc type, updates preferences.
    Returns new preferences dict (immutable pattern).
    """
```

**Logic:**
- For each document type in the stratified evaluation output, compare accuracy across extraction methods.
- If method A accuracy > method B accuracy for a doc type with >= `min_sample_count` documents, set method A as preferred with method B as fallback.
- Merge with existing preferences: new data overrides old data for the same doc type. Doc types not in the new eval report retain their existing preferences.
- Sample counts accumulate across runs (not reset).

**Called by:** `pipeline_orchestrator.py` after `evaluation_agent()` completes.

#### Modified: `services/extraction/router.py`

Add a new Rule 0 at the top of `select_extractor_with_reason()`:

```python
# Rule 0: Learned preference (if available and sufficient samples)
prefs = _load_routing_preferences()
if prefs and doc_type in prefs.get("method_preferences", {}):
    pref = prefs["method_preferences"][doc_type]
    if pref.get("sample_count", 0) >= prefs.get("min_sample_count", 5):
        return {
            "selected_extractor": pref["preferred"],
            "reason": f"learned_preference_{doc_type}",
            "classifier": classify_pdf(document_diagnostics),
        }
```

If learned preference doesn't exist or has insufficient samples, the existing Rules 1-7 fire unchanged.

### 2. Slow Path: LLM Review Agent

#### New File: `services/extraction/extraction_skill.md`

```yaml
---
name: pdf-extraction-routing
description: Learned patterns for PDF extraction method selection
version: 1.0.0
updated_at: "2026-04-08T14:30:00Z"
review_count: 0
---

# PDF Extraction Routing Skill

## Method Characteristics
- pdftotext: Fast, reliable for simple layouts, struggles with nested tables
- docling: Better table extraction, slower, higher compute cost

## Document Type Patterns
(populated by review agent over time)

## Known Edge Cases
(populated by review agent over time)
```

#### New Module: `services/extraction/skill_reviewer.py`

```python
def should_review(runs_since_last_review: int, review_interval: int = 5) -> bool:
    """Check if enough runs have accumulated to trigger a review."""

def run_review(
    eval_reports: list[dict],
    current_skill_path: Path,
    current_prefs_path: Path,
    model: str = "gpt-4.1-mini",
    max_iterations: int = 8,
) -> ReviewResult:
    """
    Spawn a background review agent that:
    1. Reads accumulated eval reports
    2. Reads current extraction_skill.md
    3. Reads current routing_preferences.json
    4. Decides whether to patch the skill with qualitative insights
    
    Returns ReviewResult with patches_applied and summary.
    """

def skill_patch(
    skill_path: Path,
    old_string: str,
    new_string: str,
) -> bool:
    """
    Atomic find-and-replace in skill file.
    Uses temp file + os.replace() for crash safety.
    """
```

**Review prompt:**
```
Review the accumulated extraction evaluation reports below.

Focus on:
1. Are there document types or PDF sources where one method consistently
   outperforms the other in ways the metrics alone don't capture?
2. Are there failure patterns (high fallback rate, anomalies) that suggest
   preprocessing or configuration changes?
3. Did any routing decisions contradict expectations?

If you find actionable patterns, patch the extraction skill using the
skill_patch tool. If nothing worth saving, say "Nothing to save." and stop.
```

**Review agent implementation:** The review agent is a function call, not a separate process. `skill_reviewer.run_review()` constructs a prompt with the eval reports and current skill content, sends it to the configured LLM via the same HTTP client the native manager uses (`openai`-compatible endpoint), parses the response for patch instructions, and applies them via `skill_patch()`. No agent framework needed — it's a single LLM call with structured output parsing.

**Review agent constraints:**
- Max 8 tool iterations (LLM calls in the review loop)
- Tools limited to: `skill_patch`, `skill_read`
- Model: configurable, default `gpt-4.1-mini`
- Runs in background thread (daemon, non-blocking)
- Failures logged but don't interrupt pipeline

**How the skill is consumed:** The extraction skill content is injected into the routing agent's system context when `routing_agent()` runs in the pipeline orchestrator, providing qualitative guidance alongside the quantitative preferences.

### 3. Regression Protection

#### Fast Path Regression

```
Run N:   eval -> preference_updater writes routing_preferences.json
         (snapshots previous to routing_preferences.prev.json first)
Run N+1: uses new preferences -> eval -> regression guard
         PASS: preferences confirmed, baseline updated
         FAIL: restore routing_preferences.prev.json
```

#### Slow Path Regression

Same pattern:
```
Review agent patches extraction_skill.md
(snapshots previous to extraction_skill.prev.md first)
Next run using updated skill -> eval -> regression guard
PASS: skill confirmed
FAIL: restore extraction_skill.prev.md
```

**Rollback mechanism:** Before any write, snapshot current file to `*.prev.*`. On regression failure, `os.replace(prev_path, current_path)`. Atomic, single-file, no new infrastructure.

**Existing tolerances apply.** The regression guard already handles:
- Direction inference (accuracy = higher is better, fallback_rate = lower is better)
- Configurable tolerance per metric
- Decision outputs (pass/fail/baseline_initialized/baseline_updated)

### 4. Configuration

Added to pipeline orchestrator config:

```yaml
learning_loop:
  enabled: true
  fast_path:
    enabled: true
    min_sample_count: 5
    preferences_file: "services/extraction/routing_preferences.json"
  slow_path:
    enabled: true
    review_interval: 5
    max_review_iterations: 8
    review_model: "gpt-4.1-mini"
    skill_file: "services/extraction/extraction_skill.md"
  regression:
    auto_rollback: true
```

All features independently toggleable. Both paths disabled by default until explicitly enabled.

## File Layout

```
services/extraction/
├── router.py                      # MODIFIED — add Rule 0 learned preference lookup
├── routing_preferences.json       # NEW — learned method preferences (generated)
├── routing_preferences.prev.json  # NEW — rollback snapshot (generated)
├── preference_updater.py          # NEW — metrics -> preferences logic
├── extraction_skill.md            # NEW — qualitative knowledge (Hermes-style)
├── extraction_skill.prev.md       # NEW — rollback snapshot (generated)
└── skill_reviewer.py              # NEW — background LLM review agent

services/orchestrator/
└── pipeline_orchestrator.py       # MODIFIED — wire updater + review trigger
```

## Dependencies

**None.** The preference updater is pure Python (JSON read/write). The skill reviewer uses the same LLM client infrastructure the native manager already uses.

## Testing Strategy

1. **Unit tests for preference_updater.py:**
   - Given an eval report with clear winner per doc type, preferences reflect that
   - Sample count accumulation across runs
   - Merge with existing preferences (new overrides old, missing preserved)
   - Edge case: all methods equal accuracy

2. **Unit tests for router.py Rule 0:**
   - Preference exists with sufficient samples -> uses learned preference
   - Preference exists with insufficient samples -> falls through to existing rules
   - No preferences file -> falls through to existing rules
   - Preferences file malformed -> falls through to existing rules (no crash)

3. **Unit tests for regression rollback:**
   - Snapshot created before update
   - Rollback restores snapshot
   - Atomic write (no partial files)

4. **Integration test:**
   - Full pipeline run -> preferences updated -> next run uses preferences -> regression guard validates
   - Simulated regression -> rollback fires -> preferences restored

5. **Skill reviewer tests:**
   - Review trigger fires at correct interval
   - Review agent patches skill file
   - Review agent respects max iterations cap
   - Background thread failure doesn't crash pipeline

## Future Extensions

These are explicitly **out of scope** for this design but noted for future phases:

1. **Cockpit chat learning loop** — Same pattern applied to `/chat` endpoint, evolving RAG prompts based on session quality signals
2. **Router optimizer learning** — Feed extraction learning patterns into the model router for better task-to-model matching
3. **Multi-platform gateway** — Hermes-style Telegram/Discord/Slack interface for querying tenn (use case #1 from initial discussion)
4. **Cross-document learning** — Track extraction patterns across PDF providers/sources, not just document types

## References

- [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) — Learning loop architecture, skill management, memory system
- `services/extraction/router.py` — Current hardcoded extraction routing
- `services/orchestrator/pipeline_orchestrator.py` — Pipeline stages and evaluation output format
- `services/evaluation/scorer.py` — Metric comparison and accuracy calculation
- `autodev/runtime/regression_guard.py` — Baseline protection and rollback logic
