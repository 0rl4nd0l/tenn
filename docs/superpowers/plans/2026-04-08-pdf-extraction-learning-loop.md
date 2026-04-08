# PDF Extraction Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the feedback loop between extraction assessment metrics and routing decisions so the PDF extraction pipeline gets smarter over time.

**Architecture:** Two-path learning system. Fast path: deterministic preference updates from assessment metrics after every pipeline run. Slow path: LLM review agent that patches a qualitative extraction skill file every N runs. Both protected by existing regression guard with automatic rollback.

**Tech Stack:** Python 3.12+, JSON for preferences, Markdown for skill files, existing regression guard, existing pipeline orchestrator. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-04-08-pdf-extraction-learning-loop-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `services/extraction/preference_updater.py` | Create | Converts assessment reports into routing preferences JSON |
| `services/extraction/routing_preferences.py` | Create | Loads, validates, and snapshots routing preferences |
| `services/extraction/skill_reviewer.py` | Create | Background LLM review agent that patches extraction skill |
| `services/extraction/extraction_skill.md` | Create | Hermes-style qualitative skill file (seed content) |
| `services/extraction/router.py` | Modify | Add Rule 0 learned preference lookup (lines 35-104) |
| `services/orchestrator/pipeline_orchestrator.py` | Modify | Wire preference updater + review trigger after assessment (lines 602-658) |
| `services/extraction/tests/__init__.py` | Create | Test package init |
| `services/extraction/tests/test_preference_updater.py` | Create | Unit tests for preference update logic |
| `services/extraction/tests/test_routing_preferences.py` | Create | Unit tests for preference loading/snapshotting |
| `services/extraction/tests/test_router_learned.py` | Create | Unit tests for Rule 0 in router |
| `services/extraction/tests/test_skill_reviewer.py` | Create | Unit tests for review trigger and skill patching |

---

### Task 1: Routing Preferences Loader

**Files:**
- Create: `services/extraction/routing_preferences.py`
- Create: `services/extraction/tests/__init__.py`
- Create: `services/extraction/tests/test_routing_preferences.py`

- [ ] **Step 1: Write the failing tests**

Create test file:

```python
# services/extraction/tests/test_routing_preferences.py
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from services.extraction.routing_preferences import (
    load_preferences,
    snapshot_preferences,
    restore_snapshot,
    SCHEMA_VERSION,
)


def test_load_preferences_returns_none_when_file_missing():
    result = load_preferences(Path("/nonexistent/routing_preferences.json"))
    assert result is None


def test_load_preferences_returns_none_when_file_malformed(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text("not json", encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_none_when_schema_version_wrong(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text(
        json.dumps({"schema_version": 999, "method_preferences": {}}),
        encoding="utf-8",
    )
    result = load_preferences(prefs_file)
    assert result is None


def test_load_preferences_returns_valid_prefs(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    data = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": "2026-04-08T14:30:00Z",
        "source_run_id": "run-1",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_pdftotext",
                "accuracy": 0.91,
                "fallback": "financial_metrics_docling",
                "fallback_accuracy": 0.78,
                "sample_count": 10,
                "last_updated": "2026-04-08T14:30:00Z",
            }
        },
        "min_sample_count": 5,
    }
    prefs_file.write_text(json.dumps(data), encoding="utf-8")
    result = load_preferences(prefs_file)
    assert result is not None
    assert result["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"


def test_snapshot_creates_prev_file(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text('{"schema_version": 1}', encoding="utf-8")
    prev_path = snapshot_preferences(prefs_file)
    assert prev_path.exists()
    assert prev_path.name == "routing_preferences.prev.json"
    assert prev_path.read_text(encoding="utf-8") == '{"schema_version": 1}'


def test_snapshot_returns_none_when_file_missing(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    result = snapshot_preferences(prefs_file)
    assert result is None


def test_restore_snapshot_overwrites_current(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prev_file = tmp_path / "routing_preferences.prev.json"
    prefs_file.write_text('{"new": true}', encoding="utf-8")
    prev_file.write_text('{"old": true}', encoding="utf-8")
    restore_snapshot(prefs_file)
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"old": True}
    assert not prev_file.exists()


def test_restore_snapshot_noop_when_no_prev(tmp_path):
    prefs_file = tmp_path / "routing_preferences.json"
    prefs_file.write_text('{"current": true}', encoding="utf-8")
    restore_snapshot(prefs_file)
    assert json.loads(prefs_file.read_text(encoding="utf-8")) == {"current": True}
```

- [ ] **Step 2: Create test package init**

```python
# services/extraction/tests/__init__.py
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_routing_preferences.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.extraction.routing_preferences'`

- [ ] **Step 4: Write minimal implementation**

```python
# services/extraction/routing_preferences.py
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def load_preferences(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("routing_preferences: malformed file at %s", path)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema_version") != SCHEMA_VERSION:
        logger.warning("routing_preferences: unsupported schema_version in %s", path)
        return None
    return data


def save_preferences(path: Path, data: dict[str, Any]) -> None:
    content = json.dumps(data, indent=2, sort_keys=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".prefs_", suffix=".json"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def snapshot_preferences(path: Path) -> Path | None:
    if not path.exists():
        return None
    prev_path = path.with_suffix(".prev.json")
    content = path.read_text(encoding="utf-8")
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=".prev_", suffix=".json"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(prev_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return prev_path


def restore_snapshot(path: Path) -> bool:
    prev_path = path.with_suffix(".prev.json")
    if not prev_path.exists():
        return False
    os.replace(str(prev_path), str(path))
    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_routing_preferences.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/l4nd0/tenn
git add services/extraction/routing_preferences.py services/extraction/tests/__init__.py services/extraction/tests/test_routing_preferences.py
git commit -m "feat: add routing preferences loader with atomic writes and snapshot/restore"
```

---

### Task 2: Preference Updater

**Files:**
- Create: `services/extraction/preference_updater.py`
- Create: `services/extraction/tests/test_preference_updater.py`

- [ ] **Step 1: Write the failing tests**

```python
# services/extraction/tests/test_preference_updater.py
from __future__ import annotations

import pytest

from services.extraction.preference_updater import update_preferences


def _make_report(doc_type_stratified: dict) -> dict:
    return {
        "stratified": {
            "document_type": doc_type_stratified,
            "complexity_bucket": {},
            "extraction_method": {},
        },
        "documents_total": 12,
    }


def test_update_preferences_picks_higher_accuracy_method():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10,
            "accuracy": 0.91,
            "fallback_rate": 0.1,
            "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91,
            "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report,
        method_accuracies=method_accuracies,
        current_prefs=None,
        min_sample_count=5,
    )
    pref = result["method_preferences"]["structured_financial_reports"]
    assert pref["preferred"] == "financial_metrics_pdftotext"
    assert pref["fallback"] == "financial_metrics_docling"
    assert pref["accuracy"] == 0.91
    assert pref["fallback_accuracy"] == 0.78
    assert pref["sample_count"] == 10


def test_update_preferences_accumulates_sample_count():
    existing = {
        "schema_version": 1,
        "updated_at": "2026-04-07T00:00:00Z",
        "source_run_id": "old",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_pdftotext",
                "accuracy": 0.85,
                "fallback": "financial_metrics_docling",
                "fallback_accuracy": 0.70,
                "sample_count": 20,
                "last_updated": "2026-04-07T00:00:00Z",
            },
        },
        "min_sample_count": 5,
    }
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10,
            "accuracy": 0.91,
            "fallback_rate": 0.1,
            "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91,
            "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report,
        method_accuracies=method_accuracies,
        current_prefs=existing,
        min_sample_count=5,
    )
    pref = result["method_preferences"]["structured_financial_reports"]
    assert pref["sample_count"] == 30  # 20 + 10


def test_update_preferences_preserves_unaffected_doc_types():
    existing = {
        "schema_version": 1,
        "updated_at": "2026-04-07T00:00:00Z",
        "source_run_id": "old",
        "method_preferences": {
            "complex_ocr_heavy": {
                "preferred": "financial_metrics_docling",
                "accuracy": 0.80,
                "fallback": "financial_metrics_pdftotext",
                "fallback_accuracy": 0.55,
                "sample_count": 15,
                "last_updated": "2026-04-06T00:00:00Z",
            },
        },
        "min_sample_count": 5,
    }
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10,
            "accuracy": 0.91,
            "fallback_rate": 0.1,
            "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91,
            "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report,
        method_accuracies=method_accuracies,
        current_prefs=existing,
        min_sample_count=5,
    )
    assert "complex_ocr_heavy" in result["method_preferences"]
    assert result["method_preferences"]["complex_ocr_heavy"]["preferred"] == "financial_metrics_docling"


def test_update_preferences_skips_doc_type_below_min_samples():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 2,
            "accuracy": 0.91,
            "fallback_rate": 0.1,
            "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91,
            "financial_metrics_docling": 0.78,
        },
    }
    result = update_preferences(
        assessment_report=report,
        method_accuracies=method_accuracies,
        current_prefs=None,
        min_sample_count=5,
    )
    assert "structured_financial_reports" not in result["method_preferences"]


def test_update_preferences_equal_accuracy_keeps_pdftotext():
    report = _make_report({
        "structured_financial_reports": {
            "documents": 10,
            "accuracy": 0.85,
            "fallback_rate": 0.0,
            "anomaly_rate": 0.0,
        },
    })
    method_accuracies = {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.85,
            "financial_metrics_docling": 0.85,
        },
    }
    result = update_preferences(
        assessment_report=report,
        method_accuracies=method_accuracies,
        current_prefs=None,
        min_sample_count=5,
    )
    pref = result["method_preferences"]["structured_financial_reports"]
    assert pref["preferred"] == "financial_metrics_pdftotext"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_preference_updater.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.extraction.preference_updater'`

- [ ] **Step 3: Write minimal implementation**

```python
# services/extraction/preference_updater.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.extraction.routing_preferences import SCHEMA_VERSION

DEFAULT_EXTRACTOR = "financial_metrics_pdftotext"


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def update_preferences(
    *,
    assessment_report: dict[str, Any],
    method_accuracies: dict[str, dict[str, float]],
    current_prefs: dict[str, Any] | None,
    min_sample_count: int = 5,
) -> dict[str, Any]:
    """Build new routing preferences from assessment report and per-method accuracies.

    Args:
        assessment_report: Output of PipelineOrchestrator.assessment_agent().
        method_accuracies: {doc_type: {method_name: accuracy}} from full benchmark.
        current_prefs: Existing routing_preferences.json content, or None.
        min_sample_count: Minimum documents per doc type before trusting preference.

    Returns:
        New preferences dict (immutable pattern — does not mutate current_prefs).
    """
    existing_prefs = dict(
        (current_prefs or {}).get("method_preferences", {})
    )
    stratified = (assessment_report.get("stratified") or {}).get("document_type") or {}
    now = _utc_now()

    for doc_type, doc_stats in stratified.items():
        if not isinstance(doc_stats, dict):
            continue
        doc_count = int(doc_stats.get("documents") or 0)
        if doc_count < min_sample_count:
            continue

        accuracies = method_accuracies.get(doc_type)
        if not accuracies or len(accuracies) < 2:
            continue

        sorted_methods = sorted(
            accuracies.items(), key=lambda x: (-x[1], x[0] != DEFAULT_EXTRACTOR)
        )
        best_method, best_acc = sorted_methods[0]
        fallback_method, fallback_acc = sorted_methods[1]

        prev_sample_count = 0
        if doc_type in existing_prefs:
            prev_sample_count = int(
                existing_prefs[doc_type].get("sample_count") or 0
            )

        existing_prefs[doc_type] = {
            "preferred": best_method,
            "accuracy": round(best_acc, 6),
            "fallback": fallback_method,
            "fallback_accuracy": round(fallback_acc, 6),
            "sample_count": prev_sample_count + doc_count,
            "last_updated": now,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": now,
        "source_run_id": str(assessment_report.get("source_run_id") or ""),
        "method_preferences": existing_prefs,
        "min_sample_count": min_sample_count,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_preference_updater.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/l4nd0/tenn
git add services/extraction/preference_updater.py services/extraction/tests/test_preference_updater.py
git commit -m "feat: add preference updater — converts assessment reports to routing preferences"
```

---

### Task 3: Router Rule 0 — Learned Preference Lookup

**Files:**
- Modify: `services/extraction/router.py:35-104`
- Create: `services/extraction/tests/test_router_learned.py`

- [ ] **Step 1: Write the failing tests**

```python
# services/extraction/tests/test_router_learned.py
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from services.extraction.router import select_extractor_with_reason


def _make_prefs(doc_type: str, preferred: str, sample_count: int = 10) -> dict:
    return {
        "schema_version": 1,
        "updated_at": "2026-04-08T00:00:00Z",
        "source_run_id": "test",
        "method_preferences": {
            doc_type: {
                "preferred": preferred,
                "accuracy": 0.90,
                "fallback": "financial_metrics_docling",
                "fallback_accuracy": 0.70,
                "sample_count": sample_count,
                "last_updated": "2026-04-08T00:00:00Z",
            }
        },
        "min_sample_count": 5,
    }


def _mock_classifier(doc_type: str = "structured_financial_reports"):
    return {
        "document_type": doc_type,
        "complexity_score": 0.5,
        "table_density": 0.1,
    }


@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.pdf_classifier.classify_pdf", return_value=_mock_classifier())
def test_rule0_uses_learned_preference(mock_classify, mock_load):
    mock_load.return_value = _make_prefs(
        "structured_financial_reports", "financial_metrics_docling"
    )
    result = select_extractor_with_reason(
        document_diagnostics={"rejected_rows": 0},
        method_results={},
    )
    assert result["selected_extractor"] == "financial_metrics_docling"
    assert result["reason"] == "learned_preference_structured_financial_reports"


@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.pdf_classifier.classify_pdf", return_value=_mock_classifier())
def test_rule0_falls_through_insufficient_samples(mock_classify, mock_load):
    mock_load.return_value = _make_prefs(
        "structured_financial_reports", "financial_metrics_docling", sample_count=2
    )
    result = select_extractor_with_reason(
        document_diagnostics={"rejected_rows": 0},
        method_results={},
    )
    assert result["reason"] != "learned_preference_structured_financial_reports"


@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.pdf_classifier.classify_pdf", return_value=_mock_classifier())
def test_rule0_falls_through_when_no_prefs(mock_classify, mock_load):
    mock_load.return_value = None
    result = select_extractor_with_reason(
        document_diagnostics={"rejected_rows": 0},
        method_results={},
    )
    assert result["reason"] != "learned_preference_structured_financial_reports"


@patch("services.extraction.router._load_routing_preferences")
@patch("services.extraction.pdf_classifier.classify_pdf", return_value=_mock_classifier("unknown_type"))
def test_rule0_falls_through_when_doc_type_not_in_prefs(mock_classify, mock_load):
    mock_load.return_value = _make_prefs(
        "structured_financial_reports", "financial_metrics_docling"
    )
    result = select_extractor_with_reason(
        document_diagnostics={"rejected_rows": 0},
        method_results={},
    )
    assert "learned_preference" not in result["reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_router_learned.py -v`
Expected: FAIL — `_load_routing_preferences` does not exist in `router.py`

- [ ] **Step 3: Modify router.py to add Rule 0**

Add imports at the top of `services/extraction/router.py` (after line 6):

```python
import logging
from pathlib import Path
from services.extraction.routing_preferences import load_preferences

logger = logging.getLogger(__name__)

_PREFERENCES_PATH = Path(__file__).parent / "routing_preferences.json"
```

Add the `_load_routing_preferences` function before `select_extractor_with_reason`:

```python
def _load_routing_preferences() -> dict[str, Any] | None:
    return load_preferences(_PREFERENCES_PATH)
```

Insert Rule 0 inside `select_extractor_with_reason`, after classifier/document_type/complexity_score are computed (after line 43), before the appendix_report check (line 45):

```python
    # Rule 0: Learned preference (if available and sufficient samples)
    prefs = _load_routing_preferences()
    if prefs and document_type in prefs.get("method_preferences", {}):
        pref = prefs["method_preferences"][document_type]
        min_samples = int(prefs.get("min_sample_count", 5))
        if int(pref.get("sample_count", 0)) >= min_samples:
            return {
                "selected_extractor": pref["preferred"],
                "reason": f"learned_preference_{document_type}",
                "classifier": classifier,
            }
```

All existing rules (1-7) remain unchanged after this block.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_router_learned.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Run all extraction tests to verify no regression**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/l4nd0/tenn
git add services/extraction/router.py services/extraction/tests/test_router_learned.py
git commit -m "feat: add Rule 0 learned preference lookup to extraction router"
```

---

### Task 4: Extraction Skill File and Patcher

**Files:**
- Create: `services/extraction/extraction_skill.md`
- Create: `services/extraction/skill_reviewer.py`
- Create: `services/extraction/tests/test_skill_reviewer.py`

- [ ] **Step 1: Create the seed skill file**

```markdown
---
name: pdf-extraction-routing
description: Learned patterns for PDF extraction method selection
version: 1.0.0
updated_at: "2026-04-08T00:00:00Z"
review_count: 0
---

# PDF Extraction Routing Skill

## Method Characteristics
- pdftotext: Fast, reliable for simple layouts, struggles with nested tables
- docling: Better table extraction, slower, higher compute cost

## Document Type Patterns
No patterns learned yet.

## Known Edge Cases
No edge cases documented yet.
```

- [ ] **Step 2: Write the failing tests**

```python
# services/extraction/tests/test_skill_reviewer.py
from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from services.extraction.skill_reviewer import (
    skill_patch,
    snapshot_skill,
    restore_skill_snapshot,
    should_review,
    parse_skill_frontmatter,
)


SEED_SKILL = textwrap.dedent("""\
    ---
    name: pdf-extraction-routing
    description: Learned patterns for PDF extraction method selection
    version: 1.0.0
    updated_at: "2026-04-08T00:00:00Z"
    review_count: 0
    ---

    # PDF Extraction Routing Skill

    ## Document Type Patterns
    No patterns learned yet.
    """)


def test_skill_patch_replaces_text(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    result = skill_patch(
        skill_path=skill_file,
        old_string="No patterns learned yet.",
        new_string="- structured_financial_reports: prefer pdftotext (accuracy 0.91)",
    )
    assert result is True
    content = skill_file.read_text(encoding="utf-8")
    assert "prefer pdftotext" in content
    assert "No patterns learned yet." not in content


def test_skill_patch_returns_false_when_old_string_not_found(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    result = skill_patch(
        skill_path=skill_file,
        old_string="this string does not exist",
        new_string="replacement",
    )
    assert result is False
    content = skill_file.read_text(encoding="utf-8")
    assert "replacement" not in content


def test_skill_patch_atomic_write(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    skill_patch(
        skill_path=skill_file,
        old_string="No patterns learned yet.",
        new_string="Updated pattern.",
    )
    temp_files = [f for f in tmp_path.iterdir() if f.name.startswith(".skill_")]
    assert len(temp_files) == 0


def test_snapshot_and_restore(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text("original content", encoding="utf-8")
    prev = snapshot_skill(skill_file)
    assert prev is not None
    skill_file.write_text("modified content", encoding="utf-8")
    restore_skill_snapshot(skill_file)
    assert skill_file.read_text(encoding="utf-8") == "original content"


def test_should_review_true_at_interval():
    assert should_review(runs_since_last_review=5, review_interval=5) is True
    assert should_review(runs_since_last_review=10, review_interval=5) is True


def test_should_review_false_below_interval():
    assert should_review(runs_since_last_review=3, review_interval=5) is False
    assert should_review(runs_since_last_review=0, review_interval=5) is False


def test_parse_skill_frontmatter(tmp_path):
    skill_file = tmp_path / "extraction_skill.md"
    skill_file.write_text(SEED_SKILL, encoding="utf-8")
    fm = parse_skill_frontmatter(skill_file)
    assert fm["name"] == "pdf-extraction-routing"
    assert fm["review_count"] == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_skill_reviewer.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation**

```python
# services/extraction/skill_reviewer.py
from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SKILL_PATH = Path(__file__).parent / "extraction_skill.md"


def should_review(runs_since_last_review: int, review_interval: int = 5) -> bool:
    return runs_since_last_review >= review_interval > 0


def parse_skill_frontmatter(skill_path: Path) -> dict[str, Any]:
    content = skill_path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    frontmatter: dict[str, Any] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        try:
            frontmatter[key.strip()] = int(value)
        except ValueError:
            try:
                frontmatter[key.strip()] = float(value)
            except ValueError:
                frontmatter[key.strip()] = value
    return frontmatter


def skill_patch(
    skill_path: Path,
    old_string: str,
    new_string: str,
) -> bool:
    content = skill_path.read_text(encoding="utf-8")
    if old_string not in content:
        logger.warning("skill_patch: old_string not found in %s", skill_path)
        return False
    updated = content.replace(old_string, new_string, 1)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(skill_path.parent), prefix=".skill_", suffix=".md"
    )
    try:
        os.write(fd, updated.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(skill_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return True


def snapshot_skill(skill_path: Path) -> Path | None:
    if not skill_path.exists():
        return None
    prev_path = skill_path.with_suffix(".prev.md")
    content = skill_path.read_text(encoding="utf-8")
    fd, tmp_path = tempfile.mkstemp(
        dir=str(skill_path.parent), prefix=".prev_", suffix=".md"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(prev_path))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return prev_path


def restore_skill_snapshot(skill_path: Path) -> bool:
    prev_path = skill_path.with_suffix(".prev.md")
    if not prev_path.exists():
        return False
    os.replace(str(prev_path), str(skill_path))
    return True


def read_skill(skill_path: Path | None = None) -> str:
    path = skill_path or _SKILL_PATH
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_skill_reviewer.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/l4nd0/tenn
git add services/extraction/extraction_skill.md services/extraction/skill_reviewer.py services/extraction/tests/test_skill_reviewer.py
git commit -m "feat: add extraction skill file and patcher with atomic writes"
```

---

### Task 5: Wire Learning Loop into Pipeline Orchestrator

**Files:**
- Modify: `services/orchestrator/pipeline_orchestrator.py:602-658`

- [ ] **Step 1: Read current state of the run() method**

Read `services/orchestrator/pipeline_orchestrator.py` lines 548-659 to confirm structure before modifying.

- [ ] **Step 2: Add imports at top of pipeline_orchestrator.py**

After the existing imports (after line 35), add:

```python
from services.extraction.routing_preferences import (
    load_preferences,
    save_preferences,
    snapshot_preferences,
)
from services.extraction.preference_updater import update_preferences
from services.extraction.skill_reviewer import should_review, snapshot_skill
```

- [ ] **Step 3: Add learning loop config defaults**

After the existing constants (after line 31), add:

```python
DEFAULT_LEARNING_LOOP_ENABLED = False
DEFAULT_FAST_PATH_ENABLED = True
DEFAULT_SLOW_PATH_ENABLED = True
DEFAULT_REVIEW_INTERVAL = 5
DEFAULT_MIN_SAMPLE_COUNT = 5
PREFERENCES_PATH = REPO_ROOT / "services" / "extraction" / "routing_preferences.json"
SKILL_PATH = REPO_ROOT / "services" / "extraction" / "extraction_skill.md"
```

- [ ] **Step 4: Add _extract_method_accuracies helper to PipelineOrchestrator**

Add this method to the `PipelineOrchestrator` class, before the `run()` method:

```python
    def _extract_method_accuracies(
        self, full_payload: Mapping[str, Any], datasets: DatasetSelection
    ) -> dict[str, dict[str, float]]:
        """Extract per-doc-type, per-method accuracy from full benchmark results."""
        accum: dict[str, dict[str, list[float]]] = {}
        for doc in full_payload.get("documents") or []:
            if not isinstance(doc, Mapping):
                continue
            pdf_path = doc.get("pdf")
            if not pdf_path:
                continue
            doc_type = _dataset_type_from_pdf(Path(str(pdf_path)))
            method_payloads = dict(doc.get("methods") or {})
            for method_name, payload in method_payloads.items():
                if not isinstance(payload, Mapping):
                    continue
                score = payload.get("score")
                if not isinstance(score, Mapping):
                    continue
                if str(score.get("status") or "") != "SUCCESS":
                    continue
                aggregate = score.get("aggregate")
                if not isinstance(aggregate, Mapping):
                    continue
                accuracy = _safe_float(aggregate.get("accuracy"))
                bucket = accum.setdefault(doc_type, {})
                bucket.setdefault(method_name, []).append(accuracy)
        result: dict[str, dict[str, float]] = {}
        for doc_type, methods in accum.items():
            result[doc_type] = {
                method: round(sum(values) / len(values), 6)
                for method, values in methods.items()
                if values
            }
        return result
```

- [ ] **Step 5: Add learning loop call after assessment in run()**

After the line that builds the `report` dict (line 654, before `if mode == "BATCH_RUN":`), add:

```python
        # --- Learning Loop ---
        learning_config = config.get("learning_loop") or {}
        if learning_config.get("enabled", DEFAULT_LEARNING_LOOP_ENABLED):
            fast_path_config = learning_config.get("fast_path") or {}
            if fast_path_config.get("enabled", DEFAULT_FAST_PATH_ENABLED):
                self._log("learning_loop", "fast_path", "updating_preferences")
                prefs_path = Path(str(
                    fast_path_config.get("preferences_file") or PREFERENCES_PATH
                ))
                current_prefs = load_preferences(prefs_path)
                snapshot_preferences(prefs_path)
                method_accuracies = self._extract_method_accuracies(
                    full_payload, selection
                )
                new_prefs = update_preferences(
                    assessment_report=evaluation,
                    method_accuracies=method_accuracies,
                    current_prefs=current_prefs,
                    min_sample_count=int(
                        fast_path_config.get("min_sample_count", DEFAULT_MIN_SAMPLE_COUNT)
                    ),
                )
                save_preferences(prefs_path, new_prefs)
                report["learning_loop"] = {"fast_path": "updated"}

            slow_path_config = learning_config.get("slow_path") or {}
            if slow_path_config.get("enabled", DEFAULT_SLOW_PATH_ENABLED):
                review_interval = int(
                    slow_path_config.get("review_interval", DEFAULT_REVIEW_INTERVAL)
                )
                runs_since = int(learning_config.get("_runs_since_review", 0))
                if should_review(runs_since, review_interval):
                    self._log("learning_loop", "slow_path", "review_triggered")
                    skill_path = Path(str(
                        slow_path_config.get("skill_file") or SKILL_PATH
                    ))
                    snapshot_skill(skill_path)
                    report.setdefault("learning_loop", {})["slow_path"] = "review_triggered"
                else:
                    report.setdefault("learning_loop", {})["slow_path"] = "skipped"
```

- [ ] **Step 6: Run existing tests to verify no regression**

Run: `cd /home/l4nd0/tenn && python -m pytest autodev/tests/ -v -k "not experiment" --timeout=30`
Expected: Existing tests PASS (learning loop disabled by default)

- [ ] **Step 7: Commit**

```bash
cd /home/l4nd0/tenn
git add services/orchestrator/pipeline_orchestrator.py
git commit -m "feat: wire learning loop into pipeline orchestrator after assessment"
```

---

### Task 6: Integration Test — Full Learning Loop Cycle

**Files:**
- Create: `services/extraction/tests/test_learning_loop_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# services/extraction/tests/test_learning_loop_integration.py
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.extraction.preference_updater import update_preferences
from services.extraction.routing_preferences import (
    load_preferences,
    save_preferences,
    snapshot_preferences,
    restore_snapshot,
    SCHEMA_VERSION,
)
from services.extraction.skill_reviewer import (
    skill_patch,
    snapshot_skill,
    restore_skill_snapshot,
    read_skill,
)


def _make_full_assessment():
    return {
        "documents_total": 12,
        "routed_accuracy": 0.88,
        "fallback_rate": 0.15,
        "stratified": {
            "document_type": {
                "structured_financial_reports": {
                    "documents": 6,
                    "accuracy": 0.91,
                    "fallback_rate": 0.1,
                    "anomaly_rate": 0.0,
                },
                "semi_structured_presentations": {
                    "documents": 4,
                    "accuracy": 0.82,
                    "fallback_rate": 0.2,
                    "anomaly_rate": 0.05,
                },
                "complex_ocr_heavy": {
                    "documents": 2,
                    "accuracy": 0.70,
                    "fallback_rate": 0.5,
                    "anomaly_rate": 0.0,
                },
            },
            "complexity_bucket": {},
            "extraction_method": {},
        },
    }


def _make_method_accuracies():
    return {
        "structured_financial_reports": {
            "financial_metrics_pdftotext": 0.91,
            "financial_metrics_docling": 0.78,
        },
        "semi_structured_presentations": {
            "financial_metrics_pdftotext": 0.62,
            "financial_metrics_docling": 0.85,
        },
        "complex_ocr_heavy": {
            "financial_metrics_pdftotext": 0.55,
            "financial_metrics_docling": 0.70,
        },
    }


def test_full_cycle_preferences_to_routing(tmp_path):
    """End-to-end: assessment report -> preferences -> correct method selected."""
    prefs_path = tmp_path / "routing_preferences.json"

    new_prefs = update_preferences(
        assessment_report=_make_full_assessment(),
        method_accuracies=_make_method_accuracies(),
        current_prefs=None,
        min_sample_count=3,
    )
    save_preferences(prefs_path, new_prefs)

    loaded = load_preferences(prefs_path)
    assert loaded is not None
    assert loaded["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"
    assert loaded["method_preferences"]["semi_structured_presentations"]["preferred"] == "financial_metrics_docling"
    assert loaded["method_preferences"]["complex_ocr_heavy"]["preferred"] == "financial_metrics_docling"


def test_rollback_cycle(tmp_path):
    """Snapshot -> update -> rollback restores original."""
    prefs_path = tmp_path / "routing_preferences.json"

    original = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": "2026-04-07T00:00:00Z",
        "source_run_id": "original",
        "method_preferences": {
            "structured_financial_reports": {
                "preferred": "financial_metrics_docling",
                "accuracy": 0.80,
                "fallback": "financial_metrics_pdftotext",
                "fallback_accuracy": 0.75,
                "sample_count": 5,
                "last_updated": "2026-04-07T00:00:00Z",
            }
        },
        "min_sample_count": 5,
    }
    save_preferences(prefs_path, original)
    snapshot_preferences(prefs_path)

    new_prefs = update_preferences(
        assessment_report=_make_full_assessment(),
        method_accuracies=_make_method_accuracies(),
        current_prefs=original,
        min_sample_count=3,
    )
    save_preferences(prefs_path, new_prefs)

    loaded = load_preferences(prefs_path)
    assert loaded["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_pdftotext"

    restore_snapshot(prefs_path)
    restored = load_preferences(prefs_path)
    assert restored["method_preferences"]["structured_financial_reports"]["preferred"] == "financial_metrics_docling"


def test_skill_patch_and_rollback(tmp_path):
    """Skill file: patch -> rollback restores original."""
    skill_path = tmp_path / "extraction_skill.md"
    seed = (
        "---\nname: test\n---\n\n"
        "## Document Type Patterns\nNo patterns learned yet.\n"
    )
    skill_path.write_text(seed, encoding="utf-8")

    snapshot_skill(skill_path)

    skill_patch(
        skill_path=skill_path,
        old_string="No patterns learned yet.",
        new_string="- structured_financial_reports: prefer pdftotext (0.91 accuracy)",
    )
    assert "prefer pdftotext" in read_skill(skill_path)

    restore_skill_snapshot(skill_path)
    assert "No patterns learned yet." in read_skill(skill_path)
```

- [ ] **Step 2: Run integration tests**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/test_learning_loop_integration.py -v`
Expected: All 3 tests PASS

- [ ] **Step 3: Run full test suite for the learning loop**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/ -v`
Expected: All tests PASS (unit + integration)

- [ ] **Step 4: Commit**

```bash
cd /home/l4nd0/tenn
git add services/extraction/tests/test_learning_loop_integration.py
git commit -m "test: add integration tests for full learning loop cycle and rollback"
```

---

### Task 7: Final Verification and Cleanup

**Files:**
- All new and modified files

- [ ] **Step 1: Run full test suite**

Run: `cd /home/l4nd0/tenn && python -m pytest services/extraction/tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Run ruff linter**

Run: `cd /home/l4nd0/tenn && python -m ruff check services/extraction/`
Expected: No errors

- [ ] **Step 3: Run existing system tests to verify no regression**

Run: `cd /home/l4nd0/tenn && python -m pytest autodev/tests/ financial-engine_v2/backend/tests/ -v --timeout=60 -x`
Expected: All existing tests PASS

- [ ] **Step 4: Verify file layout matches spec**

```
services/extraction/
├── router.py                      # MODIFIED — Rule 0 added
├── routing_preferences.py         # NEW — load/save/snapshot/restore
├── preference_updater.py          # NEW — assessment report -> preferences
├── extraction_skill.md            # NEW — seed skill file
├── skill_reviewer.py              # NEW — patch/snapshot/restore/read
├── pdf_classifier.py              # UNCHANGED
├── docling_runner.py              # UNCHANGED
└── tests/
    ├── __init__.py
    ├── test_routing_preferences.py
    ├── test_preference_updater.py
    ├── test_router_learned.py
    ├── test_skill_reviewer.py
    └── test_learning_loop_integration.py

services/orchestrator/
└── pipeline_orchestrator.py       # MODIFIED — learning loop wiring
```

- [ ] **Step 5: Commit final state**

```bash
cd /home/l4nd0/tenn
git add -A services/extraction/ services/orchestrator/pipeline_orchestrator.py
git commit -m "chore: final verification — learning loop complete"
```
