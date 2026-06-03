from __future__ import annotations

from datetime import date
import re
from dateutil import parser as dtparser

EXTRACTOR_VERSION = "ollama_json_v1"

KEYWORD_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("accounting policies", re.compile(r"accounting\s+polic(?:y|ies)", re.I)),
    ("cash flow", re.compile(r"cash\s*flows?", re.I)),
    ("revenue", re.compile(r"\brevenue\b", re.I)),
    ("net debt", re.compile(r"net\s+debt", re.I)),
    ("profit after tax", re.compile(r"profit\s+after\s+tax|npat", re.I)),
)


def _clip(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text[:limit]


def build_extraction_text(
    text: str,
    *,
    max_chars: int = 18000,
    head_chars: int = 6000,
    tail_chars: int = 6000,
    keyword_window_chars: int = 3000,
) -> str:
    """Build a bounded extraction sample from long PDF text.

    Short documents pass through unchanged. Long documents preserve the start,
    the end, and the first matching finance/accounting keyword window so the LLM
    sees both report context and likely metric/note sections.
    """
    text = text or ""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text

    sections: list[tuple[str, str]] = []
    sections.append(("HEAD", _clip(text, head_chars)))

    for label, pattern in KEYWORD_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        half = max(1, keyword_window_chars // 2)
        start = max(0, match.start() - half)
        end = min(len(text), match.end() + half)
        sections.append((f"KEYWORD:{label}", text[start:end]))
        break

    sections.append(("TAIL", text[-tail_chars:] if tail_chars > 0 else ""))

    rendered: list[str] = []
    for label, body in sections:
        if not body:
            continue
        rendered.append(f"[{label}]\n{body.strip()}")

    out = "\n\n".join(rendered)
    if len(out) <= max_chars:
        return out

    # Keep all section labels visible by trimming section bodies proportionally.
    labels_overhead = sum(len(f"[{label}]\n\n\n") for label, body in sections if body)
    budget = max(0, max_chars - labels_overhead)
    nonempty = [(label, body.strip()) for label, body in sections if body]
    per_section = max(1, budget // max(1, len(nonempty)))
    out = "\n\n".join(f"[{label}]\n{body[:per_section]}" for label, body in nonempty)
    return out[:max_chars]


def build_prompt(text: str) -> str:
    clipped = build_extraction_text(text or "", max_chars=18000)
    return f"""You are a financial document extraction engine. Output ONLY valid JSON.
Schema:
{{
  "period_type": "Q|H|A|null",
  "period_end": "YYYY-MM-DD|null",
  "metrics": {{
    "revenue": "number|null",
    "ebit": "number|null",
    "np_attributable": "number|null",
    "operating_cf": "number|null",
    "investing_cf": "number|null",
    "financing_cf": "number|null",
    "capex": "number|null",
    "cash_end": "number|null",
    "net_debt": "number|null",
    "shares_outstanding": "number|null"
  }},
  "metric_provenance": {{
    "<metric_name>": {{
      "page": "number|null",
      "excerpt": "short exact source text|null",
      "unit": "string|null",
      "currency": "string|null",
      "scale": "ones|thousands|millions|billions|null"
    }}
  }},
  "confidence_metrics": "0..1",
  "risk_summary": "string|null",
  "risk_bullets": "array<string>|null",
  "guidance_summary": "string|null",
  "material_changes": "string|null",
  "confidence_narrative": "0..1"
}}

Document text:
""" + clipped


def parse_period_end(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return dtparser.parse(s).date()
    except Exception:
        return None
