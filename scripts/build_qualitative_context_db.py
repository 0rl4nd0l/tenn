#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import datetime
import types
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from health_guard import assert_healthy, load_health_snapshot


SECTION_PATTERNS: Dict[str, List[re.Pattern[str]]] = {
    "mda": [
        re.compile(r"\bmanagement(?:'s)?\s+discussion\s+and\s+analysis\b", re.IGNORECASE),
        re.compile(r"\boperating\s+and\s+financial\s+review\b", re.IGNORECASE),
        re.compile(r"\breview\s+of\s+operations\b", re.IGNORECASE),
        re.compile(r"\bfinancial\s+review\b", re.IGNORECASE),
    ],
    "risk": [
        re.compile(r"\brisk\s+factors?\b", re.IGNORECASE),
        re.compile(r"\bprincipal\s+risks?\b", re.IGNORECASE),
        re.compile(r"\bmaterial\s+risks?\b", re.IGNORECASE),
        re.compile(r"\bkey\s+risks?\b", re.IGNORECASE),
    ],
    "chairman_commentary": [
        re.compile(r"\bchair(?:man|person)'?s\s+(?:letter|message|statement|review)\b", re.IGNORECASE),
        re.compile(r"\bceo'?s\s+(?:letter|message|review)\b", re.IGNORECASE),
        re.compile(r"\bmanaging\s+director'?s\s+(?:letter|message|review)\b", re.IGNORECASE),
    ],
    "cashflow_commentary": [
        re.compile(r"\bcash\s*flow\s+(?:commentary|discussion|analysis|review)\b", re.IGNORECASE),
        re.compile(r"\bliquidity\s+and\s+capital\s+resources\b", re.IGNORECASE),
        re.compile(r"\bcash\s*flow\b", re.IGNORECASE),
        re.compile(r"\bworking\s+capital\b", re.IGNORECASE),
    ],
}

GENERIC_HEADING_RE = re.compile(r"^[A-Z][A-Z\s&/\-(),]{4,}$")
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
RERANK_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
ALLOWLIST_TOKEN_RE = re.compile(r"[A-Za-z0-9]{1,12}")
COMPANY_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,6}$")
_ST_MODEL_CACHE: Dict[Tuple[str, str], Any] = {}


@dataclass
class SectionSpan:
    file_path: Path
    company: str
    section: str
    text: str
    corpus: str = "company"
    doc_type: str = "other"
    doc_date: str = ""
    bad_metadata_reason: str = ""


@dataclass
class ChunkRecord:
    chunk_id: str
    company: str
    file: str
    section: str
    text: str
    corpus: str = "company"
    doc_type: str = "other"
    doc_date: str = ""
    source: str = ""
    ticker: str = ""
    topic: str = ""
    url: str = ""
    title: str = ""
    published_at: str = ""
    bad_metadata_reason: str = ""


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def extract_pdf_text(pdf: Path) -> str:
    cp = subprocess.run(
        ["pdftotext", str(pdf), "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return clean_text(cp.stdout)


def find_pdfs(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


def normalize_heading(line: str) -> str:
    s = re.sub(r"\s+", " ", line.strip())
    s = s.strip(":.-")
    return s


def detect_section_heading(line: str) -> Optional[str]:
    heading = normalize_heading(line)
    if not heading:
        return None
    if not is_probable_heading(line):
        return None
    for section, patterns in SECTION_PATTERNS.items():
        for pat in patterns:
            if pat.search(heading):
                return section
    return None


def is_probable_heading(line: str) -> bool:
    heading = normalize_heading(line)
    if not heading:
        return False
    if len(heading) > 110:
        return False
    if heading.endswith("."):
        return False
    if GENERIC_HEADING_RE.match(heading):
        return True
    words = heading.split()
    if 1 <= len(words) <= 12 and sum(ch.isalpha() for ch in heading) >= 6:
        title_ratio = sum(1 for w in words if w and w[0].isupper()) / len(words)
        upper_ratio = sum(ch.isupper() for ch in heading if ch.isalpha()) / max(
            1, sum(ch.isalpha() for ch in heading)
        )
        return upper_ratio > 0.7 or title_ratio >= 0.75
    return False


def derive_company(pdf: Path, pdf_root: Path) -> str:
    def is_ticker_token(token: str) -> bool:
        if not re.fullmatch(r"[A-Z0-9]{2,6}", token):
            return False
        # ASX tickers are alphanumeric but should include at least one letter.
        return bool(re.search(r"[A-Z]", token))

    # ASX docs are nested as docs/<TICKER>/<category>/<file>.pdf.
    # Prefer the first root-relative path segment when it looks like a ticker.
    try:
        rel_parts = pdf.relative_to(pdf_root).parts
    except ValueError:
        rel_parts = ()
    if rel_parts:
        root_segment = rel_parts[0].upper()
        if is_ticker_token(root_segment):
            return root_segment

    if pdf.parent != pdf_root:
        return pdf.parent.name
    stem = pdf.stem

    # MarketIndex filenames commonly follow:
    # DD-MM-YY_HHMMam_TICKER_slug_...
    for part in stem.split("_"):
        if is_ticker_token(part):
            return part
    for m in re.finditer(r"(?<![A-Za-z0-9])[A-Z0-9]{2,6}(?![A-Za-z0-9])", stem):
        token = m.group(0)
        if is_ticker_token(token):
            return token
    return stem.split("_")[0].split("-")[0]


def infer_doc_type(file_path: Path, text: str) -> str:
    name = file_path.name.lower()
    head = text[:4000].lower()

    if any(k in name for k in ("textbook", "university edition", "edition", "playbook", "ift-notes", "notes")):
        return "textbook"
    if any(k in head for k in ("research foundation", "isbn", "chapter ", "monograph")):
        return "textbook"

    if any(k in name for k in ("investor-presentation", "results-presentation", "corporate-presentation", "presentation")):
        return "presentation"

    if any(k in name for k in ("annual-report", "financial-report", "half-year", "half year", "appendix-4e", "appendix-4d", "appendix 4e", "appendix 4d")):
        return "annual_report"

    if any(k in name for k in ("research", "journal", "study", "analysis")):
        return "research"

    return "announcement"


def infer_doc_date(file_path: Path) -> str:
    stem = file_path.stem
    m = re.search(r"(?<!\d)(\d{2})-(\d{2})-(\d{2})(?!\d)", stem)
    if m:
        dd, mm, yy = m.groups()
        year = 2000 + int(yy)
        try:
            return datetime.date(year, int(mm), int(dd)).isoformat()
        except ValueError:
            pass

    m = re.search(r"(20\d{2})[-_](\d{2})[-_](\d{2})", stem)
    if m:
        yyyy, mm, dd = m.groups()
        try:
            return datetime.date(int(yyyy), int(mm), int(dd)).isoformat()
        except ValueError:
            pass

    return ""


def derive_title_from_file_path(file_path: Path) -> str:
    stem = file_path.stem
    title = re.sub(r"^\d{2}-\d{2}-\d{2}_\d+(?:am|pm)_", "", stem, flags=re.IGNORECASE)
    title = re.sub(r"_[0-9A-F]{6,}$", "", title, flags=re.IGNORECASE)
    title = title.replace("_", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title or stem


def coalesce_company_chunk_title(file_path: Path, fallback_company: str, fallback_section: str) -> str:
    title = derive_title_from_file_path(file_path)
    if title:
        return title
    fallback = " ".join(bit for bit in [str(fallback_company or "").strip(), str(fallback_section or "").strip()] if bit)
    return fallback or file_path.stem


def coalesce_company_published_at(doc_date: str, file_path: Path) -> str:
    value = str(doc_date or "").strip()
    if value:
        return value
    return infer_doc_date(file_path)


def enrich_company_row_metadata(row: Dict[str, str]) -> Dict[str, str]:
    out = dict(row)
    if str(out.get("corpus") or "company") != "company":
        return out
    file_path = Path(str(out.get("file") or "").strip() or "untitled.pdf")
    title = str(out.get("title") or "").strip()
    if not title:
        out["title"] = coalesce_company_chunk_title(
            file_path=file_path,
            fallback_company=str(out.get("company") or ""),
            fallback_section=str(out.get("section") or ""),
        )
    published_at = str(out.get("published_at") or "").strip()
    if not published_at:
        out["published_at"] = coalesce_company_published_at(
            doc_date=str(out.get("doc_date") or ""),
            file_path=file_path,
        )
    return out


def normalize_ticker_symbol(value: str) -> str:
    sym = re.sub(r"[^A-Za-z0-9.\-]", "", str(value).strip().upper())
    if not sym:
        return ""
    if len(sym) > 12:
        return ""
    return sym


def canonical_company_symbol(value: str) -> str:
    sym = re.sub(r"[^A-Za-z0-9]", "", str(value or "").strip().upper())
    if not sym:
        return ""
    if len(sym) > 6:
        return ""
    return sym


def _is_valid_company_symbol(value: str) -> bool:
    sym = canonical_company_symbol(value)
    if not sym:
        return False
    if not COMPANY_SYMBOL_RE.fullmatch(sym):
        return False
    return bool(re.search(r"[A-Z]", sym))


def validate_company_symbol(value: str, allowlist: Optional[Set[str]] = None) -> Tuple[str, str]:
    raw = str(value or "").strip()
    sym = canonical_company_symbol(raw)
    if not raw:
        return "UNKNOWN", "missing_company"
    if not sym:
        return "UNKNOWN", "invalid_company_format"
    if not _is_valid_company_symbol(sym):
        return "UNKNOWN", "invalid_company_format"
    if allowlist is not None and allowlist and sym not in allowlist:
        return "UNKNOWN", "company_not_in_allowlist"
    return sym, ""


def _collect_allowlist_tokens(value: Any, out: Set[str]) -> None:
    if value is None:
        return
    if isinstance(value, dict):
        for k, v in value.items():
            _collect_allowlist_tokens(k, out)
            _collect_allowlist_tokens(v, out)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_allowlist_tokens(item, out)
        return
    text = str(value).strip()
    if not text:
        return
    for token in ALLOWLIST_TOKEN_RE.findall(text):
        sym = canonical_company_symbol(token)
        if _is_valid_company_symbol(sym):
            out.add(sym)


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except Exception:
                continue
            if isinstance(row, dict):
                yield row


def load_company_allowlist(path: Path) -> Set[str]:
    if not path.exists():
        raise RuntimeError(f"Company allowlist path does not exist: {path}")
    out: Set[str] = set()
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            _collect_allowlist_tokens(payload, out)
            return out
        except Exception:
            pass
    if suffix == ".jsonl":
        for row in _iter_jsonl(path):
            _collect_allowlist_tokens(row, out)
        return out
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            _collect_allowlist_tokens(line, out)
    return out


def summarize_company_metadata(records: Sequence[ChunkRecord]) -> Dict[str, Any]:
    company_counts = collections.Counter(str(rec.company or "UNKNOWN") for rec in records)
    invalid_reason_counts = collections.Counter(
        str(rec.bad_metadata_reason or "").strip()
        for rec in records
        if str(rec.bad_metadata_reason or "").strip()
    )
    total = int(len(records))
    invalid_count = int(sum(invalid_reason_counts.values()))
    ratio_pct = (100.0 * invalid_count / total) if total > 0 else 0.0
    top_companies = [
        {"company": company, "count": int(count)}
        for company, count in company_counts.most_common(20)
    ]
    invalid_reasons = {reason: int(count) for reason, count in invalid_reason_counts.items()}
    return {
        "total_chunks": total,
        "invalid_company_count": invalid_count,
        "invalid_company_ratio_pct": round(ratio_pct, 4),
        "company_distribution_top": top_companies,
        "invalid_reasons": invalid_reasons,
    }


def company_validation_gate_failed(
    summary: Dict[str, Any],
    threshold_pct: float,
    min_count: int,
) -> Tuple[bool, str]:
    invalid_count = int(summary.get("invalid_company_count", 0) or 0)
    ratio_pct = float(summary.get("invalid_company_ratio_pct", 0.0) or 0.0)
    threshold = float(max(0.0, threshold_pct))
    minimum = int(max(0, min_count))
    tripped = invalid_count >= minimum and ratio_pct > threshold
    reason = (
        f"invalid_company_ratio_pct={ratio_pct:.4f} "
        f"threshold_pct={threshold:.4f} invalid_company_count={invalid_count} min_count={minimum}"
    )
    return tripped, reason


def serialize_tickers(values: Sequence[str]) -> str:
    seen = set()
    out: List[str] = []
    for raw in values:
        sym = normalize_ticker_symbol(str(raw))
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    out.sort()
    if not out:
        return ""
    return "|" + "|".join(out) + "|"


def parse_ticker_blob(blob: str) -> List[str]:
    raw = str(blob or "").strip()
    if not raw:
        return []
    if "|" in raw:
        parts = [p for p in raw.split("|") if p.strip()]
    else:
        parts = [p for p in re.split(r"[,\s;/]+", raw) if p.strip()]
    out = [normalize_ticker_symbol(p) for p in parts]
    return sorted({x for x in out if x})


def ticker_blob_contains(blob: str, ticker: str) -> bool:
    target = normalize_ticker_symbol(ticker)
    if not target:
        return False
    return target in set(parse_ticker_blob(blob))


def extract_target_sections(
    file_path: Path,
    text: str,
    company: str,
    bad_metadata_reason: str = "",
) -> List[SectionSpan]:
    out: List[SectionSpan] = []
    lines = text.splitlines()
    current_section: Optional[str] = None
    buffer: List[str] = []

    def flush() -> None:
        nonlocal buffer, current_section
        if current_section and buffer:
            payload = "\n".join(x for x in buffer if x.strip()).strip()
            if payload:
                out.append(
                    SectionSpan(
                        file_path=file_path,
                        company=company,
                        section=current_section,
                        text=payload,
                        bad_metadata_reason=bad_metadata_reason,
                    )
                )
        buffer = []

    for raw in lines:
        line = raw.strip()
        if not line:
            if current_section and buffer and buffer[-1] != "":
                buffer.append("")
            continue

        matched = detect_section_heading(line)
        if matched:
            flush()
            current_section = matched
            continue

        if current_section and is_probable_heading(line):
            flush()
            current_section = None
            continue

        if current_section:
            buffer.append(line)

    flush()
    return out


def extract_full_document_span(
    file_path: Path,
    text: str,
    company: str,
    corpus: str,
    doc_type: str,
    doc_date: str,
    bad_metadata_reason: str = "",
) -> List[SectionSpan]:
    payload = clean_text(text).strip()
    if not payload:
        return []
    return [
        SectionSpan(
            file_path=file_path,
            company=company,
            section="fulltext_context",
            text=payload,
            corpus=corpus,
            doc_type=doc_type,
            doc_date=doc_date,
            bad_metadata_reason=bad_metadata_reason,
        )
    ]


def chunk_text(text: str, max_chars: int = 1200, overlap_words: int = 60) -> List[str]:
    words = text.split()
    if not words:
        return []

    chunks: List[str] = []
    i = 0
    while i < len(words):
        out: List[str] = []
        chars = 0
        j = i
        while j < len(words):
            w = words[j]
            add = len(w) + (1 if out else 0)
            if chars + add > max_chars and out:
                break
            out.append(w)
            chars += add
            j += 1
        chunks.append(" ".join(out))
        if j >= len(words):
            break
        i = max(i + 1, j - overlap_words)
    return chunks


def build_chunk_records(spans: Sequence[SectionSpan], max_chars: int, overlap_words: int) -> List[ChunkRecord]:
    records: List[ChunkRecord] = []
    seen = set()

    for span in spans:
        chunks = chunk_text(span.text, max_chars=max_chars, overlap_words=overlap_words)
        for idx, text in enumerate(chunks):
            dedupe_key = (span.corpus, span.company, str(span.file_path), span.section, text)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            # Use content hash in chunk_id to avoid collisions when a document
            # contains multiple separated spans of the same section.
            digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{span.corpus}:{span.company}:{span.file_path.name}:{span.section}:{idx}:{digest}"
            ticker_blob = serialize_tickers([span.company]) if span.corpus == "company" else ""
            title = (
                coalesce_company_chunk_title(span.file_path, span.company, span.section)
                if span.corpus == "company"
                else ""
            )
            published_at = (
                coalesce_company_published_at(span.doc_date, span.file_path)
                if span.corpus == "company"
                else ""
            )
            records.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    company=span.company,
                    file=str(span.file_path),
                    section=span.section,
                    text=text,
                    corpus=span.corpus,
                    doc_type=span.doc_type,
                    doc_date=span.doc_date,
                    ticker=ticker_blob,
                    title=title,
                    published_at=published_at,
                    bad_metadata_reason=str(span.bad_metadata_reason or ""),
                )
            )
    return records


def l2_normalize(v: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return [0.0 for _ in v]
    return [x / norm for x in v]


def hash_embed(text: str, dim: int = 384) -> List[float]:
    v = [0.0] * dim
    for tok in (t.lower() for t in TOKEN_RE.findall(text)):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        h = int.from_bytes(digest[:8], byteorder="big", signed=False)
        pos = h % dim
        sign = -1.0 if (h & 1) else 1.0
        v[pos] += sign
    return l2_normalize(v)


def sentence_transformer_model_name(model: str) -> str:
    aliases = {
        "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
        "e5-large-v2": "intfloat/e5-large-v2",
        "nomic-embed-text": "nomic-ai/nomic-embed-text-v1.5",
    }
    return aliases.get(model, model)


def choose_sentence_transformers_device(preferred: str) -> str:
    mode = (preferred or "auto").strip().lower()
    strict_cuda = mode in {"cuda_strict", "strict_cuda"}
    if strict_cuda:
        mode = "cuda"
    if mode == "cpu":
        return "cpu"
    if mode == "cuda":
        try:
            import torch
        except Exception as exc:
            if strict_cuda:
                raise RuntimeError("CUDA strict mode requested but PyTorch is not available.") from exc
            return "cpu"
        if not torch.cuda.is_available() or torch.cuda.device_count() <= 0:
            if strict_cuda:
                raise RuntimeError("CUDA strict mode requested but no CUDA GPU is visible to PyTorch.")
            return "cpu"
        try:
            major, _minor = torch.cuda.get_device_capability(0)
            # PyTorch 2.10 wheels in this environment support >= sm_70 only.
            if major < 7:
                if strict_cuda:
                    raise RuntimeError(
                        f"CUDA strict mode requested but GPU capability sm_{major}x is unsupported for this PyTorch build."
                    )
                return "cpu"
        except RuntimeError:
            raise
        except Exception as exc:
            if strict_cuda:
                raise RuntimeError("CUDA strict mode requested but CUDA capability check failed.") from exc
            return "cpu"
        return "cuda"
    try:
        import torch
    except Exception:
        return "cpu"
    if not torch.cuda.is_available():
        return "cpu"
    try:
        major, _minor = torch.cuda.get_device_capability(0)
        # PyTorch 2.10 wheels in this environment support >= sm_70 only.
        if major < 7:
            return "cpu"
    except Exception:
        return "cpu"
    return "cuda"


def embed_sentence_transformers(
    texts: Sequence[str],
    model_name: str,
    device: str = "auto",
    batch_size: int = 16,
) -> List[List[float]]:
    # setuptools>=82 removed pkg_resources, but older accelerate paths still import it.
    try:
        import pkg_resources  # type: ignore  # noqa: F401
    except ModuleNotFoundError:
        try:
            import importlib.metadata as importlib_metadata
        except Exception:
            importlib_metadata = None
        if importlib_metadata is not None:
            shim = types.ModuleType("pkg_resources")

            class _Dist:
                def __init__(self, version: str) -> None:
                    self.version = version

            def _get_distribution(name: str) -> _Dist:
                try:
                    return _Dist(str(importlib_metadata.version(name)))
                except importlib_metadata.PackageNotFoundError as exc:  # type: ignore[attr-defined]
                    raise ModuleNotFoundError(f"No package metadata for '{name}'") from exc

            shim.get_distribution = _get_distribution  # type: ignore[attr-defined]
            sys.modules["pkg_resources"] = shim

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        msg = str(exc)
        if "cached_download" in msg and "huggingface_hub" in msg:
            raise RuntimeError(
                "Incompatible 'sentence-transformers' / 'huggingface_hub' versions in your environment. "
                "For this repo's current dependency set, repair with: "
                "financial-engine_v2/.venv/bin/pip install --upgrade "
                "\"huggingface-hub>=0.25,<0.26\""
            ) from exc
        raise RuntimeError(
            "Missing dependency: sentence-transformers. Install with: pip install sentence-transformers"
        ) from exc

    resolved = sentence_transformer_model_name(model_name)
    strict_cuda = str(device or "").strip().lower() in {"cuda_strict", "strict_cuda"}
    run_device = choose_sentence_transformers_device(device)
    cache_key = (resolved, run_device)
    model = _ST_MODEL_CACHE.get(cache_key)
    if model is None:
        try:
            model = SentenceTransformer(resolved, device=run_device)
        except Exception as exc:
            msg = str(exc)
            if "pkg_resources" in msg:
                raise RuntimeError(
                    "Incompatible 'setuptools' / 'accelerate' / 'transformers' runtime in your environment. "
                    "Your stack expects pkg_resources, which is removed in newer setuptools. "
                    "Repair with: financial-engine_v2/.venv/bin/pip install --upgrade \"setuptools<81\""
                ) from exc
            raise
        _ST_MODEL_CACHE[cache_key] = model
    payload = [f"passage: {t}" if "e5" in model_name.lower() else t for t in texts]
    try:
        vectors = model.encode(
            payload,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=max(1, int(batch_size)),
        )
    except Exception as exc:
        if run_device == "cuda" and not strict_cuda:
            print(
                f"[warn] sentence-transformers CUDA failed ({exc}); retrying on CPU.",
                file=sys.stderr,
            )
            cache_key = (resolved, "cpu")
            model = _ST_MODEL_CACHE.get(cache_key)
            if model is None:
                model = SentenceTransformer(resolved, device="cpu")
                _ST_MODEL_CACHE[cache_key] = model
            vectors = model.encode(
                payload,
                normalize_embeddings=True,
                show_progress_bar=True,
                batch_size=max(1, int(batch_size)),
            )
        else:
            raise
    return [list(map(float, row)) for row in vectors]


def embed_ollama(texts: Sequence[str], model_name: str, endpoint: str) -> List[List[float]]:
    out: List[List[float]] = []
    for text in texts:
        payload = json.dumps({"model": model_name, "prompt": text}).encode("utf-8")
        req = urllib.request.Request(
            endpoint.rstrip("/") + "/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Could not reach Ollama embeddings endpoint: {exc}") from exc
        vec = body.get("embedding")
        if not isinstance(vec, list):
            raise RuntimeError("Unexpected Ollama response; missing 'embedding' list")
        out.append(l2_normalize([float(x) for x in vec]))
    return out


def embed_texts(
    texts: Sequence[str],
    backend: str,
    model_name: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
) -> List[List[float]]:
    if backend == "sentence-transformers":
        return embed_sentence_transformers(texts, model_name, device=st_device, batch_size=st_batch_size)
    if backend == "ollama":
        return embed_ollama(texts, model_name, ollama_endpoint)
    if backend == "hash":
        return [hash_embed(t, dim=hash_dim) for t in texts]
    raise ValueError(f"Unknown embed backend: {backend}")


def write_jsonl(records: Sequence[ChunkRecord], vectors: Sequence[Sequence[float]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec, vec in zip(records, vectors):
            payload = {
                "chunk_id": rec.chunk_id,
                "company": rec.company,
                "file": rec.file,
                "section": rec.section,
                "corpus": rec.corpus,
                "doc_type": rec.doc_type,
                "doc_date": rec.doc_date,
                "source": rec.source,
                "ticker": rec.ticker,
                "topic": rec.topic,
                "url": rec.url,
                "title": rec.title,
                "published_at": rec.published_at,
                "bad_metadata_reason": rec.bad_metadata_reason,
                "text": rec.text,
                "embedding": list(vec),
            }
            f.write(json.dumps(payload) + "\n")


def sqlite_columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    rows = cur.execute(f"PRAGMA table_info({table})").fetchall()
    return [str(r[1]) for r in rows]


def store_sqlite(records: Sequence[ChunkRecord], vectors: Sequence[Sequence[float]], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS context_chunks (
                chunk_id TEXT PRIMARY KEY,
                corpus TEXT NOT NULL DEFAULT 'company',
                doc_type TEXT NOT NULL DEFAULT 'other',
                doc_date TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                ticker TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                bad_metadata_reason TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL,
                file TEXT NOT NULL,
                section TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT NOT NULL
            )
            """
        )
        if "corpus" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN corpus TEXT NOT NULL DEFAULT 'company'")
        if "doc_type" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN doc_type TEXT NOT NULL DEFAULT 'other'")
        if "doc_date" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN doc_date TEXT NOT NULL DEFAULT ''")
        if "source" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN source TEXT NOT NULL DEFAULT ''")
        if "ticker" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN ticker TEXT NOT NULL DEFAULT ''")
        if "topic" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN topic TEXT NOT NULL DEFAULT ''")
        if "url" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN url TEXT NOT NULL DEFAULT ''")
        if "title" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN title TEXT NOT NULL DEFAULT ''")
        if "published_at" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN published_at TEXT NOT NULL DEFAULT ''")
        if "bad_metadata_reason" not in sqlite_columns(cur, "context_chunks"):
            cur.execute("ALTER TABLE context_chunks ADD COLUMN bad_metadata_reason TEXT NOT NULL DEFAULT ''")

        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_corpus ON context_chunks(corpus)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_doc_type ON context_chunks(doc_type)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_doc_date ON context_chunks(doc_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_source ON context_chunks(source)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_ticker ON context_chunks(ticker)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_company ON context_chunks(company)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_context_section ON context_chunks(section)")

        rows = [
            (
                rec.chunk_id,
                rec.corpus,
                rec.doc_type,
                rec.doc_date,
                rec.source,
                rec.ticker,
                rec.topic,
                rec.url,
                rec.title,
                rec.published_at,
                rec.bad_metadata_reason,
                rec.company,
                rec.file,
                rec.section,
                rec.text,
                json.dumps(list(vec)),
            )
            for rec, vec in zip(records, vectors)
        ]
        cur.executemany(
            """
            INSERT INTO context_chunks(
                chunk_id, corpus, doc_type, doc_date, source, ticker, topic, url, title, published_at,
                bad_metadata_reason, company, file, section, text, embedding_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
                corpus=excluded.corpus,
                doc_type=excluded.doc_type,
                doc_date=excluded.doc_date,
                source=excluded.source,
                ticker=excluded.ticker,
                topic=excluded.topic,
                url=excluded.url,
                title=excluded.title,
                published_at=excluded.published_at,
                bad_metadata_reason=excluded.bad_metadata_reason,
                company=excluded.company,
                file=excluded.file,
                section=excluded.section,
                text=excluded.text,
                embedding_json=excluded.embedding_json
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def store_faiss(records: Sequence[ChunkRecord], vectors: Sequence[Sequence[float]], out_dir: Path) -> None:
    try:
        import faiss  # type: ignore
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency for FAISS backend. Install with: pip install faiss-cpu numpy") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    arr = np.array(vectors, dtype="float32")
    if arr.ndim != 2 or arr.shape[0] == 0:
        raise RuntimeError("No vectors to index")

    index = faiss.IndexFlatIP(arr.shape[1])
    index.add(arr)
    faiss.write_index(index, str(out_dir / "index.faiss"))

    meta = [
        {
            "chunk_id": rec.chunk_id,
            "corpus": rec.corpus,
            "doc_type": rec.doc_type,
            "doc_date": rec.doc_date,
            "source": rec.source,
            "ticker": rec.ticker,
            "topic": rec.topic,
            "url": rec.url,
            "title": rec.title,
            "published_at": rec.published_at,
            "bad_metadata_reason": rec.bad_metadata_reason,
            "company": rec.company,
            "file": rec.file,
            "section": rec.section,
            "text": rec.text,
        }
        for rec in records
    ]
    with (out_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def store_chroma(records: Sequence[ChunkRecord], vectors: Sequence[Sequence[float]], out_dir: Path) -> None:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("Missing dependency for Chroma backend. Install with: pip install chromadb") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(out_dir))
    collection = client.get_or_create_collection(name="qualitative_context")

    ids = [rec.chunk_id for rec in records]
    docs = [rec.text for rec in records]
    metas = [
        {
            "corpus": rec.corpus,
            "doc_type": rec.doc_type,
            "doc_date": rec.doc_date,
            "source": rec.source,
            "ticker": rec.ticker,
            "topic": rec.topic,
            "url": rec.url,
            "title": rec.title,
            "published_at": rec.published_at,
            "bad_metadata_reason": rec.bad_metadata_reason,
            "company": rec.company,
            "file": rec.file,
            "section": rec.section,
        }
        for rec in records
    ]
    collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=[list(v) for v in vectors])


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        return -1.0
    return float(sum(x * y for x, y in zip(a, b)))


RERANK_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
    "fy",
    "hy",
    "h1",
    "q1",
    "q2",
    "q3",
    "q4",
}

RERANK_TOKEN_WEIGHTS = {
    "results": 0.025,
    "announcement": 0.022,
    "presentation": 0.022,
    "report": 0.018,
    "appendix": 0.018,
    "annual": 0.016,
    "financial": 0.014,
    "dividend": 0.025,
    "buy": 0.012,
    "back": 0.012,
}


def _rerank_tokens(text: str) -> List[str]:
    normalized = str(text or "").lower().replace("_", " ")
    out: List[str] = []
    for tok in RERANK_TOKEN_RE.findall(normalized):
        if len(tok) < 3:
            continue
        if tok in RERANK_STOPWORDS:
            continue
        out.append(tok)
    return out


def _build_rerank_haystack(row: Dict[str, str]) -> str:
    file_name = Path(str(row.get("file", ""))).name
    parts = [
        str(row.get("title", "")),
        file_name,
        str(row.get("section", "")),
        str(row.get("doc_type", "")),
        str(row.get("topic", "")),
    ]
    return " ".join(parts)


def doc_type_matches(row_doc_type: str, doc_type_filter: str, row: Dict[str, str]) -> bool:
    target = str(doc_type_filter or "").strip().lower()
    if not target:
        return True

    actual = str(row_doc_type or "other").strip().lower()
    if actual == target:
        return True

    hay = _build_rerank_haystack(row).lower()
    hay = hay.replace("_", "-")

    # Backward-compatible fallback: some files are semantically announcements
    # but were previously labeled as annual_report by filename heuristics.
    if target == "announcement":
        if "announcement" in hay:
            return True
        if "results-announcement" in hay:
            return True
        return False

    if target == "annual_report":
        annual_markers = (
            "annual-report",
            "annual report",
            "financial-report",
            "financial report",
            "appendix-4d",
            "appendix 4d",
            "appendix-4e",
            "appendix 4e",
            "half-year-accounts",
            "half year accounts",
            "half-yearly-report",
            "half yearly report",
        )
        return any(marker in hay for marker in annual_markers)

    return False


def lexical_rerank_bonus(query: str, row: Dict[str, str]) -> float:
    q_tokens = _rerank_tokens(query)
    if not q_tokens:
        return 0.0
    query_set = set(q_tokens)
    hay_tokens = set(_rerank_tokens(_build_rerank_haystack(row)))
    if not hay_tokens:
        return 0.0

    score = 0.0
    for tok in query_set:
        if tok in hay_tokens:
            score += RERANK_TOKEN_WEIGHTS.get(tok, 0.006)

    # Intent-level nudges for closely related announcement types.
    wants_results = "results" in query_set
    wants_announcement = "announcement" in query_set
    wants_dividend = "dividend" in query_set
    row_has_results = "results" in hay_tokens
    row_has_dividend = "dividend" in hay_tokens

    if wants_results and wants_announcement and row_has_results:
        score += 0.05
    if wants_results and row_has_dividend and not row_has_results:
        score -= 0.08
    if wants_dividend and row_has_dividend:
        score += 0.05
    if wants_dividend and row_has_results and not row_has_dividend:
        score -= 0.03

    return score


def valid_iso_date(s: str) -> bool:
    if not s:
        return False
    try:
        datetime.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def date_in_range(doc_date: str, date_from: str, date_to: str) -> bool:
    if not doc_date:
        return not (date_from or date_to)
    if date_from and doc_date < date_from:
        return False
    if date_to and doc_date > date_to:
        return False
    return True


def query_sqlite(
    db_path: Path,
    query: str,
    backend: str,
    model_name: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
    company: str,
    corpus_filter: str,
    doc_type_filter: str,
    date_from: str,
    date_to: str,
    top_k: int = 6,
    ticker_filter: str = "",
    source_filter: str = "",
    exclude_corpus_filter: str = "",
) -> List[Tuple[float, Dict[str, str]]]:
    qvec = embed_texts(
        [query],
        backend=backend,
        model_name=model_name,
        ollama_endpoint=ollama_endpoint,
        hash_dim=hash_dim,
        st_device=st_device,
        st_batch_size=st_batch_size,
    )[0]

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cols = set(sqlite_columns(cur, "context_chunks"))
        has_corpus = "corpus" in cols
        has_doc_type = "doc_type" in cols
        has_doc_date = "doc_date" in cols
        has_source = "source" in cols
        has_ticker = "ticker" in cols
        has_topic = "topic" in cols
        has_url = "url" in cols
        has_title = "title" in cols
        has_published_at = "published_at" in cols
        has_bad_metadata_reason = "bad_metadata_reason" in cols

        select_cols = ["chunk_id", "company", "file", "section", "text", "embedding_json"]
        if has_corpus:
            select_cols.append("corpus")
        if has_doc_type:
            select_cols.append("doc_type")
        if has_doc_date:
            select_cols.append("doc_date")
        if has_source:
            select_cols.append("source")
        if has_ticker:
            select_cols.append("ticker")
        if has_topic:
            select_cols.append("topic")
        if has_url:
            select_cols.append("url")
        if has_title:
            select_cols.append("title")
        if has_published_at:
            select_cols.append("published_at")
        if has_bad_metadata_reason:
            select_cols.append("bad_metadata_reason")

        base = f"SELECT {', '.join(select_cols)}"
        base += " FROM context_chunks"

        where_parts: List[str] = []
        args: List[str] = []
        if company:
            where_parts.append("company = ?")
            args.append(company)
        if has_corpus and corpus_filter:
            where_parts.append("corpus = ?")
            args.append(corpus_filter)
        if has_corpus and exclude_corpus_filter:
            where_parts.append("corpus != ?")
            args.append(exclude_corpus_filter)
        if has_doc_date and date_from:
            where_parts.append("doc_date >= ?")
            args.append(date_from)
        if has_doc_date and date_to:
            where_parts.append("doc_date <= ?")
            args.append(date_to)
        if has_source and source_filter:
            where_parts.append("LOWER(source) = LOWER(?)")
            args.append(source_filter.strip())
        normalized_ticker = normalize_ticker_symbol(ticker_filter)
        if has_ticker and normalized_ticker:
            where_parts.append("ticker LIKE ?")
            args.append(f"%|{normalized_ticker}|%")
        if where_parts:
            base += " WHERE " + " AND ".join(where_parts)

        cur.execute(base, tuple(args))

        col_idx = {name: idx for idx, name in enumerate(select_cols)}
        scored: List[Tuple[float, Dict[str, str]]] = []
        for row in cur.fetchall():
            chunk_id = str(row[col_idx["chunk_id"]])
            comp = str(row[col_idx["company"]])
            file_path = str(row[col_idx["file"]])
            section = str(row[col_idx["section"]])
            text = str(row[col_idx["text"]])
            embedding_json = row[col_idx["embedding_json"]]
            corpus = str(row[col_idx["corpus"]]) if has_corpus else "company"
            doc_type = str(row[col_idx["doc_type"]]) if has_doc_type else "other"
            doc_date = str(row[col_idx["doc_date"]]) if has_doc_date else ""
            source = str(row[col_idx["source"]]) if has_source else ""
            ticker = str(row[col_idx["ticker"]]) if has_ticker else ""
            topic = str(row[col_idx["topic"]]) if has_topic else ""
            url = str(row[col_idx["url"]]) if has_url else ""
            title = str(row[col_idx["title"]]) if has_title else ""
            published_at = str(row[col_idx["published_at"]]) if has_published_at else ""
            bad_metadata_reason = str(row[col_idx["bad_metadata_reason"]]) if has_bad_metadata_reason else ""

            if source_filter and not has_source:
                continue
            if source_filter and source.lower() != source_filter.strip().lower():
                continue

            if normalized_ticker and not has_ticker:
                if normalize_ticker_symbol(comp) != normalized_ticker:
                    continue
            elif normalized_ticker and not ticker_blob_contains(ticker, normalized_ticker):
                continue

            row_payload = {
                "chunk_id": chunk_id,
                "company": comp,
                "file": file_path,
                "section": section,
                "corpus": corpus,
                "doc_type": doc_type,
                "doc_date": doc_date,
                "source": source,
                "ticker": ticker,
                "topic": topic,
                "url": url,
                "title": title,
                "published_at": published_at,
                "bad_metadata_reason": bad_metadata_reason,
                "text": text,
            }
            row_payload = enrich_company_row_metadata(row_payload)
            if not doc_type_matches(doc_type, doc_type_filter, row_payload):
                continue

            vec = json.loads(embedding_json)
            sim = cosine(qvec, vec)
            sim += lexical_rerank_bonus(query, row_payload)
            scored.append(
                (
                    sim,
                    row_payload,
                )
            )
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]
    finally:
        conn.close()


def query_faiss(
    index_dir: Path,
    query: str,
    backend: str,
    model_name: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
    company: str,
    corpus_filter: str,
    doc_type_filter: str,
    date_from: str,
    date_to: str,
    top_k: int = 6,
    ticker_filter: str = "",
    source_filter: str = "",
    exclude_corpus_filter: str = "",
) -> List[Tuple[float, Dict[str, str]]]:
    try:
        import faiss  # type: ignore
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency for FAISS query. Install with: pip install faiss-cpu numpy") from exc

    index_path = index_dir / "index.faiss"
    meta_path = index_dir / "metadata.json"
    if not index_path.exists() or not meta_path.exists():
        raise RuntimeError(f"Missing FAISS index files in: {index_dir}")

    with meta_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    if not isinstance(metadata, list):
        raise RuntimeError(f"Invalid metadata format: {meta_path}")

    index = faiss.read_index(str(index_path))
    qvec = embed_texts(
        [query],
        backend=backend,
        model_name=model_name,
        ollama_endpoint=ollama_endpoint,
        hash_dim=hash_dim,
        st_device=st_device,
        st_batch_size=st_batch_size,
    )[0]
    qarr = np.array([qvec], dtype="float32")
    limit = min(max(1, top_k * 8), len(metadata))
    sims, ids = index.search(qarr, limit)

    normalized_ticker = normalize_ticker_symbol(ticker_filter)
    scored: List[Tuple[float, Dict[str, str]]] = []
    for score, idx in zip(sims[0].tolist(), ids[0].tolist()):
        if idx < 0 or idx >= len(metadata):
            continue
        row = metadata[idx]
        if not isinstance(row, dict):
            continue
        if company and row.get("company") != company:
            continue
        if corpus_filter and row.get("corpus", "company") != corpus_filter:
            continue
        if exclude_corpus_filter and row.get("corpus", "company") == exclude_corpus_filter:
            continue
        if not date_in_range(str(row.get("doc_date", "")), date_from=date_from, date_to=date_to):
            continue
        if source_filter and str(row.get("source", "")).lower() != source_filter.strip().lower():
            continue
        if normalized_ticker and not ticker_blob_contains(str(row.get("ticker", "")), normalized_ticker):
            continue
        row.setdefault("source", "")
        row.setdefault("ticker", "")
        row.setdefault("topic", "")
        row.setdefault("url", "")
        row.setdefault("title", "")
        row.setdefault("published_at", "")
        row.setdefault("bad_metadata_reason", "")
        row = enrich_company_row_metadata(row)
        if not doc_type_matches(str(row.get("doc_type", "other")), doc_type_filter, row):
            continue
        final_score = float(score) + lexical_rerank_bonus(query, row)
        scored.append((final_score, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def query_chroma(
    chroma_dir: Path,
    query: str,
    backend: str,
    model_name: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
    company: str,
    corpus_filter: str,
    doc_type_filter: str,
    date_from: str,
    date_to: str,
    top_k: int = 6,
    ticker_filter: str = "",
    source_filter: str = "",
    exclude_corpus_filter: str = "",
) -> List[Tuple[float, Dict[str, str]]]:
    try:
        import chromadb
    except ImportError as exc:
        raise RuntimeError("Missing dependency for Chroma query. Install with: pip install chromadb") from exc

    client = chromadb.PersistentClient(path=str(chroma_dir))
    collection = client.get_or_create_collection(name="qualitative_context")
    qvec = embed_texts(
        [query],
        backend=backend,
        model_name=model_name,
        ollama_endpoint=ollama_endpoint,
        hash_dim=hash_dim,
        st_device=st_device,
        st_batch_size=st_batch_size,
    )[0]
    where: Optional[Dict[str, Any]] = None
    filters: List[Dict[str, Any]] = []
    if company:
        filters.append({"company": company})
    if corpus_filter:
        filters.append({"corpus": corpus_filter})
    if date_from:
        filters.append({"doc_date": {"$gte": date_from}})
    if date_to:
        filters.append({"doc_date": {"$lte": date_to}})
    if source_filter:
        filters.append({"source": source_filter})

    if len(filters) == 1:
        where = filters[0]
    elif len(filters) > 1:
        where = {"$and": filters}
    result = collection.query(
        query_embeddings=[qvec],
        n_results=max(top_k, top_k * 8),
        where=where,
        include=["metadatas", "documents", "distances"],
    )
    docs = (result.get("documents") or [[]])[0]
    metas = (result.get("metadatas") or [[]])[0]
    dists = (result.get("distances") or [[]])[0]

    normalized_ticker = normalize_ticker_symbol(ticker_filter)
    out: List[Tuple[float, Dict[str, str]]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        row = dict(meta or {})
        row.setdefault("corpus", "company")
        row.setdefault("doc_type", "other")
        row.setdefault("doc_date", "")
        row.setdefault("source", "")
        row.setdefault("ticker", "")
        row.setdefault("topic", "")
        row.setdefault("url", "")
        row.setdefault("title", "")
        row.setdefault("published_at", "")
        row.setdefault("bad_metadata_reason", "")
        row = enrich_company_row_metadata(row)
        if normalized_ticker and not ticker_blob_contains(str(row.get("ticker", "")), normalized_ticker):
            continue
        row["text"] = doc or ""
        if exclude_corpus_filter and str(row.get("corpus", "company")) == exclude_corpus_filter:
            continue
        if not doc_type_matches(str(row.get("doc_type", "other")), doc_type_filter, row):
            continue
        score = (1.0 - float(dist)) + lexical_rerank_bonus(query, row)
        out.append((score, row))
    out.sort(key=lambda x: x[0], reverse=True)
    out = out[:top_k]
    return out


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build qualitative context vector DB from PDFs")
    ap.add_argument("--pdf-dir", required=True, help="Root directory containing PDFs")
    ap.add_argument("--db", choices=["sqlite", "faiss", "chroma"], default="sqlite", help="Vector storage backend")
    ap.add_argument("--out", default="reports/qualitative_context", help="Output DB path (sqlite file or directory)")
    ap.add_argument(
        "--content-scope",
        choices=["targeted", "fulltext"],
        default="targeted",
        help="Use targeted section extraction (MD&A/risk/chairman/cashflow) or full-document chunks",
    )
    ap.add_argument(
        "--fallback-fulltext",
        action="store_true",
        help="When --content-scope=targeted and no target headings are found in a PDF, index the full document instead",
    )
    ap.add_argument(
        "--corpus",
        default="company",
        help="Corpus label stored in metadata (e.g., company, reference)",
    )
    ap.add_argument(
        "--embed-backend",
        choices=["sentence-transformers", "ollama", "hash"],
        default="sentence-transformers",
        help="Embedding runtime",
    )
    ap.add_argument("--embed-model", default="bge-large-en-v1.5", help="Embedding model alias/name")
    ap.add_argument(
        "--st-device",
        choices=["auto", "cpu", "cuda", "cuda_strict"],
        default="auto",
        help="Device for sentence-transformers embeddings",
    )
    ap.add_argument("--st-batch-size", type=int, default=16, help="Batch size for sentence-transformers encode")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--hash-dim", type=int, default=384, help="Vector size for hash embeddings")
    ap.add_argument("--max-chars", type=int, default=1200, help="Max chunk size in characters")
    ap.add_argument("--overlap-words", type=int, default=60, help="Chunk overlap in words")
    ap.add_argument(
        "--company-allowlist-path",
        default="",
        help="Optional company ticker allowlist (txt/json/jsonl). Invalid symbols become UNKNOWN.",
    )
    ap.add_argument(
        "--invalid-company-fail-threshold-pct",
        type=float,
        default=1.0,
        help="Fail run when invalid company chunk ratio exceeds this pct and min count is reached.",
    )
    ap.add_argument(
        "--invalid-company-fail-min-count",
        type=int,
        default=20,
        help="Minimum invalid company chunk count required before fail threshold applies.",
    )
    ap.add_argument("--manifest-json", default="", help="Optional path to write run manifest JSON")
    ap.add_argument("--query", default="", help="Optional retrieval query to run after indexing")
    ap.add_argument("--company", default="", help="Optional company filter for retrieval query")
    ap.add_argument("--corpus-filter", default="", help="Optional corpus filter for retrieval query")
    ap.add_argument("--exclude-corpus-filter", default="", help="Optional corpus label to exclude from retrieval")
    ap.add_argument(
        "--doc-type-filter",
        choices=["announcement", "annual_report", "presentation", "textbook", "research", "news_article", "other"],
        default="",
        help="Optional doc_type filter for retrieval query",
    )
    ap.add_argument("--ticker-filter", default="", help="Optional ticker filter for retrieval query")
    ap.add_argument("--source-filter", default="", help="Optional source filter for retrieval query")
    ap.add_argument("--date-from", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--date-to", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--top-k", type=int, default=6, help="Top-k retrieval results")
    ap.add_argument(
        "--health-json",
        default="reports/research_engine_health.json",
        help="Health snapshot JSON path used for pre-run gating.",
    )
    ap.add_argument(
        "--allow-warning",
        action="store_true",
        help="Allow execution when health snapshot overall_status=warning.",
    )
    args = ap.parse_args()

    if shutil.which("pdftotext") is None:
        print("Missing dependency: pdftotext. Install: sudo apt install -y poppler-utils", file=sys.stderr)
        return 2

    pdf_root = Path(args.pdf_dir).resolve()
    if not pdf_root.exists():
        print(f"PDF directory not found: {pdf_root}", file=sys.stderr)
        return 2

    if args.date_from and not valid_iso_date(args.date_from):
        print(f"Invalid --date-from: {args.date_from}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_to and not valid_iso_date(args.date_to):
        print(f"Invalid --date-to: {args.date_to}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_from and args.date_to and args.date_from > args.date_to:
        print("--date-from cannot be after --date-to.", file=sys.stderr)
        return 2
    if float(args.invalid_company_fail_threshold_pct) < 0.0:
        print("--invalid-company-fail-threshold-pct must be >= 0.", file=sys.stderr)
        return 2
    if int(args.invalid_company_fail_min_count) < 0:
        print("--invalid-company-fail-min-count must be >= 0.", file=sys.stderr)
        return 2

    snapshot = load_health_snapshot(str(args.health_json))
    assert_healthy(snapshot, allow_warning=bool(args.allow_warning))

    manifest_path = Path(args.manifest_json).expanduser().resolve() if args.manifest_json else None
    run_started_at = datetime.datetime.utcnow()

    allowlist_path_value = str(args.company_allowlist_path or "").strip()
    company_allowlist: Optional[Set[str]] = None
    if allowlist_path_value:
        allowlist_path = Path(allowlist_path_value).expanduser().resolve()
        try:
            company_allowlist = load_company_allowlist(allowlist_path)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if not company_allowlist:
            print(f"Company allowlist is empty after parsing: {allowlist_path}", file=sys.stderr)
            return 2
        print(f"company_allowlist={allowlist_path} size={len(company_allowlist)}")

    pdfs = find_pdfs(pdf_root)
    if not pdfs:
        print(f"No PDFs found in: {pdf_root}", file=sys.stderr)
        return 2

    spans: List[SectionSpan] = []
    parse_failed_pdfs = 0
    invalid_company_docs = 0
    for pdf in pdfs:
        try:
            text = extract_pdf_text(pdf)
        except subprocess.CalledProcessError as exc:
            print(f"[warn] failed to parse {pdf}: {exc}", file=sys.stderr)
            parse_failed_pdfs += 1
            continue

        raw_company = derive_company(pdf, pdf_root)
        company, bad_metadata_reason = validate_company_symbol(raw_company, allowlist=company_allowlist)
        if bad_metadata_reason:
            invalid_company_docs += 1
        doc_type = infer_doc_type(pdf, text)
        doc_date = infer_doc_date(pdf)
        if args.content_scope == "fulltext":
            spans.extend(
                extract_full_document_span(
                    pdf,
                    text,
                    company,
                    corpus=args.corpus,
                    doc_type=doc_type,
                    doc_date=doc_date,
                    bad_metadata_reason=bad_metadata_reason,
                )
            )
            continue

        target_spans = extract_target_sections(
            pdf,
            text,
            company,
            bad_metadata_reason=bad_metadata_reason,
        )
        if target_spans:
            for sp in target_spans:
                sp.corpus = args.corpus
                sp.doc_type = doc_type
                sp.doc_date = doc_date
            spans.extend(target_spans)
            continue

        if args.fallback_fulltext:
            spans.extend(
                extract_full_document_span(
                    pdf,
                    text,
                    company,
                    corpus=args.corpus,
                    doc_type=doc_type,
                    doc_date=doc_date,
                    bad_metadata_reason=bad_metadata_reason,
                )
            )

    if not spans:
        if args.content_scope == "targeted" and not args.fallback_fulltext:
            print("No target sections found (MD&A, risk, chairman commentary, cashflow commentary).")
            return 1
        print("No content extracted from PDFs for indexing.")
        return 1

    records = build_chunk_records(spans, max_chars=args.max_chars, overlap_words=args.overlap_words)
    if not records:
        print("Sections found but no chunks generated.")
        return 1

    company_summary = summarize_company_metadata(records)
    gate_failed, gate_reason = company_validation_gate_failed(
        company_summary,
        threshold_pct=float(args.invalid_company_fail_threshold_pct),
        min_count=int(args.invalid_company_fail_min_count),
    )

    vectors = embed_texts(
        [r.text for r in records],
        backend=args.embed_backend,
        model_name=args.embed_model,
        ollama_endpoint=args.ollama_endpoint,
        hash_dim=args.hash_dim,
        st_device=args.st_device,
        st_batch_size=args.st_batch_size,
    )

    out_path = Path(args.out)
    if args.db == "sqlite":
        if out_path.suffix != ".sqlite":
            out_path = out_path / "context.sqlite"
        store_sqlite(records, vectors, out_path)
        write_jsonl(records, vectors, out_path.with_suffix(".jsonl"))
        print(f"Stored {len(records)} chunks in SQLite: {out_path}")
    elif args.db == "faiss":
        store_faiss(records, vectors, out_path)
        print(f"Stored {len(records)} chunks in FAISS dir: {out_path}")
    elif args.db == "chroma":
        store_chroma(records, vectors, out_path)
        print(f"Stored {len(records)} chunks in Chroma dir: {out_path}")
    else:
        raise AssertionError("Unhandled db backend")

    query_result_count = 0
    if args.query:
        corpus_filter = args.corpus_filter or args.corpus
        if args.db == "sqlite":
            result_rows = query_sqlite(
                db_path=out_path,
                query=args.query,
                backend=args.embed_backend,
                model_name=args.embed_model,
                ollama_endpoint=args.ollama_endpoint,
                hash_dim=args.hash_dim,
                st_device=args.st_device,
                st_batch_size=args.st_batch_size,
                company=args.company,
                corpus_filter=corpus_filter,
                doc_type_filter=args.doc_type_filter,
                date_from=args.date_from,
                date_to=args.date_to,
                top_k=args.top_k,
                ticker_filter=args.ticker_filter,
                source_filter=args.source_filter,
                exclude_corpus_filter=args.exclude_corpus_filter,
            )
        elif args.db == "faiss":
            result_rows = query_faiss(
                index_dir=out_path,
                query=args.query,
                backend=args.embed_backend,
                model_name=args.embed_model,
                ollama_endpoint=args.ollama_endpoint,
                hash_dim=args.hash_dim,
                st_device=args.st_device,
                st_batch_size=args.st_batch_size,
                company=args.company,
                corpus_filter=corpus_filter,
                doc_type_filter=args.doc_type_filter,
                date_from=args.date_from,
                date_to=args.date_to,
                top_k=args.top_k,
                ticker_filter=args.ticker_filter,
                source_filter=args.source_filter,
                exclude_corpus_filter=args.exclude_corpus_filter,
            )
        elif args.db == "chroma":
            result_rows = query_chroma(
                chroma_dir=out_path,
                query=args.query,
                backend=args.embed_backend,
                model_name=args.embed_model,
                ollama_endpoint=args.ollama_endpoint,
                hash_dim=args.hash_dim,
                st_device=args.st_device,
                st_batch_size=args.st_batch_size,
                company=args.company,
                corpus_filter=corpus_filter,
                doc_type_filter=args.doc_type_filter,
                date_from=args.date_from,
                date_to=args.date_to,
                top_k=args.top_k,
                ticker_filter=args.ticker_filter,
                source_filter=args.source_filter,
                exclude_corpus_filter=args.exclude_corpus_filter,
            )
        else:
            raise AssertionError("Unhandled db backend")

        if not result_rows:
            print("No retrieval results for that query.")
        else:
            query_result_count = len(result_rows)

            for rank, (score, row) in enumerate(result_rows, start=1):
                print(
                    f"\n[{rank}] score={score:.4f} "
                    f"corpus={row.get('corpus', '')} company={row.get('company', '')} "
                    f"doc_type={row.get('doc_type', '')} doc_date={row.get('doc_date', '')} "
                    f"source={row.get('source', '')} ticker={row.get('ticker', '')} "
                    f"section={row.get('section', '')} file={row.get('file', '')}"
                )
                print(str(row.get("text", ""))[:600].strip())

    manifest_payload = {
        "status": "failed" if gate_failed else "success",
        "error": gate_reason if gate_failed else "",
        "started_at_utc": run_started_at.replace(microsecond=0).isoformat() + "Z",
        "updated_at_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "elapsed_seconds": round((datetime.datetime.utcnow() - run_started_at).total_seconds(), 3),
        "input": {
            "pdf_dir": str(pdf_root),
            "pdf_count": len(pdfs),
            "parse_failed_pdfs": int(parse_failed_pdfs),
            "invalid_company_docs": int(invalid_company_docs),
            "content_scope": str(args.content_scope),
            "fallback_fulltext": bool(args.fallback_fulltext),
            "company_allowlist_path": allowlist_path_value,
            "company_allowlist_size": int(len(company_allowlist or set())),
        },
        "output": {
            "db": str(args.db),
            "out_path": str(out_path),
            "corpus": str(args.corpus),
            "embed_backend": str(args.embed_backend),
            "embed_model": str(args.embed_model),
            "chunks_written": int(len(records)),
            "query_result_count": int(query_result_count),
        },
        "company_validation": {
            **company_summary,
            "threshold_pct": float(args.invalid_company_fail_threshold_pct),
            "min_count": int(args.invalid_company_fail_min_count),
            "gate_failed": bool(gate_failed),
            "gate_reason": gate_reason,
        },
    }
    if manifest_path is not None:
        atomic_write_json(manifest_path, manifest_payload)

    if gate_failed:
        print(
            "Company validation gate failed: "
            f"{gate_reason}. Chunks were written with company=UNKNOWN and bad_metadata_reason.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
