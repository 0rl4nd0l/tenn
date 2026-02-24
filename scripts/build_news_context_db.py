#!/usr/bin/env python3
"""
Experimental news corpus builder for qualitative context retrieval.

This script is intentionally isolated from the filing metric extraction path.
It ingests a news dataset, normalizes metadata, applies quality/duplicate gates,
embeds chunks, and stores an independent news DB artifact.
"""

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import sqlite3
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import build_qualitative_context_db as ctx


DEFAULT_DATASET_ID = "Brianferrell787/financial-news-multisource"

COMPLIANCE_NOTICE = (
    "Compliance notice: This dataset is gated on Hugging Face with license='other'. "
    "The dataset card states that each article retains the original publisher's copyright "
    "and terms (for example Reuters/CNBC/Investing.com/Yahoo). Treat this pipeline as "
    "research-only by default unless legal review explicitly approves your production use."
)

WORD_RE = re.compile(r"[A-Za-z]+")
TICKER_PATTERNS = [
    re.compile(r"\$([A-Z]{1,6})\b"),
    re.compile(r"\b(?:NYSE|NASDAQ|ASX|LSE|TSX|HKEX|TSE)\s*[:\-]\s*([A-Z]{1,6})\b"),
]
TICKER_STOPWORDS = {
    "CEO",
    "CFO",
    "EPS",
    "USD",
    "GDP",
    "ETF",
    "IPO",
    "Q1",
    "Q2",
    "Q3",
    "Q4",
}
EN_STOPWORDS = {
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
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
}


@dataclass
class NormalizedNewsRecord:
    record_id: str
    source: str
    published_at: str
    doc_date: str
    title: str
    body: str
    ticker: str
    topic: str
    url: str


def normalize_space(value: Any) -> str:
    txt = str(value or "").replace("\r", " ").replace("\n", " ")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def normalize_text_for_dedupe(value: str) -> str:
    txt = normalize_space(value).lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def normalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    # Keep URL normalization conservative.
    raw = raw.replace(" ", "")
    raw = raw.rstrip("/")
    return raw


def parse_extra_fields(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            txt = value.strip()
            if txt:
                return txt
        else:
            txt = normalize_space(value)
            if txt:
                return txt
    return ""


def normalize_datetime(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace("/", "-")
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw

    candidates = [raw]
    if " " in raw and "T" not in raw:
        candidates.append(raw.replace(" ", "T"))
    for candidate in candidates:
        try:
            dt = datetime.datetime.fromisoformat(candidate)
            if dt.tzinfo is not None and dt.utcoffset() == datetime.timedelta(0):
                return dt.isoformat().replace("+00:00", "Z")
            return dt.isoformat()
        except ValueError:
            pass
    return ""


def iso_date(value: str) -> str:
    txt = str(value or "").strip()
    if not txt:
        return ""
    try:
        if "T" in txt:
            dt = datetime.datetime.fromisoformat(txt.replace("Z", "+00:00"))
            return dt.date().isoformat()
        return datetime.date.fromisoformat(txt).isoformat()
    except ValueError:
        return ""


def normalize_topic(value: Any) -> str:
    if isinstance(value, list):
        entries = [normalize_space(v) for v in value if normalize_space(v)]
        return ", ".join(entries[:3])
    return normalize_space(value)


def split_title_body(raw_text: str, explicit_title: str) -> Tuple[str, str]:
    text = str(raw_text or "").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    title = normalize_space(explicit_title)
    if not text:
        return title, ""

    if not title:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            first = lines[0]
            if 20 <= len(first) <= 220:
                title = first
                text = "\n".join(lines[1:]).strip()
            else:
                title = first[:220]
                text = "\n".join(lines[1:]).strip()

    body = text
    if title:
        lower_title = normalize_text_for_dedupe(title)
        lower_body = normalize_text_for_dedupe(body[: max(500, len(title) * 2)])
        if lower_title and lower_title in lower_body:
            body = body.replace(title, "", 1).strip()

    body = normalize_space(body)
    title = normalize_space(title)
    return title, body


def looks_english(text: str) -> bool:
    if not text:
        return False
    ascii_ratio = sum(1 for ch in text if ch.isascii()) / max(1, len(text))
    if ascii_ratio < 0.85:
        return False
    words = [w.lower() for w in WORD_RE.findall(text)]
    if len(words) < 25:
        return True
    stop_hits = sum(1 for w in words[:200] if w in EN_STOPWORDS)
    return stop_hits >= 5


def extract_tickers_from_value(value: Any) -> List[str]:
    if value is None:
        return []
    raw_values: List[str] = []
    if isinstance(value, list):
        raw_values = [str(v) for v in value]
    elif isinstance(value, dict):
        raw_values = [str(v) for v in value.values()]
    else:
        txt = str(value).strip()
        if not txt:
            raw_values = []
        else:
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    parsed = json.loads(txt)
                    if isinstance(parsed, list):
                        raw_values = [str(v) for v in parsed]
                    else:
                        raw_values = [txt]
                except Exception:
                    raw_values = [txt]
            else:
                raw_values = re.split(r"[,\s;/|]+", txt)

    out: List[str] = []
    for entry in raw_values:
        sym = ctx.normalize_ticker_symbol(entry)
        if not sym:
            continue
        if sym in TICKER_STOPWORDS:
            continue
        out.append(sym)
    return out


def infer_tickers(title: str, body: str, existing: Sequence[str]) -> str:
    out = list(existing)
    merged_text = f"{title} {body[:1200]}"
    for pat in TICKER_PATTERNS:
        for match in pat.findall(merged_text):
            sym = ctx.normalize_ticker_symbol(match)
            if not sym or sym in TICKER_STOPWORDS:
                continue
            out.append(sym)
    return ctx.serialize_tickers(out)


def normalize_news_row(
    row: Dict[str, Any],
    min_text_chars: int,
    keep_non_english: bool,
) -> Tuple[Optional[NormalizedNewsRecord], str]:
    extra = parse_extra_fields(row.get("extra_fields"))
    raw_text = first_non_empty(
        row.get("text"),
        row.get("body"),
        row.get("content"),
        extra.get("text"),
        extra.get("body"),
        extra.get("content"),
    )
    explicit_title = first_non_empty(
        row.get("title"),
        row.get("headline"),
        extra.get("title"),
        extra.get("headline"),
    )
    title, body = split_title_body(raw_text, explicit_title)
    if not body or len(body) < min_text_chars:
        return None, "short_text"
    if not keep_non_english and not looks_english(body):
        return None, "non_english"

    published_at = normalize_datetime(
        first_non_empty(
            row.get("published_at"),
            row.get("publish_date"),
            row.get("date"),
            extra.get("published_at"),
            extra.get("publish_date"),
            extra.get("date"),
        )
    )
    doc_date = iso_date(published_at)
    source = normalize_space(
        first_non_empty(
            row.get("source"),
            row.get("publisher"),
            extra.get("source"),
            extra.get("publisher"),
            extra.get("publisher_name"),
            extra.get("site_name"),
            "unknown",
        )
    )
    topic = normalize_topic(
        first_non_empty(
            row.get("topic"),
            row.get("category"),
            extra.get("topic"),
            extra.get("category"),
            extra.get("categories"),
        )
    )
    url = normalize_url(
        first_non_empty(
            row.get("url"),
            row.get("link"),
            extra.get("url"),
            extra.get("link"),
            extra.get("article_url"),
        )
    )
    row_id = first_non_empty(
        row.get("id"),
        row.get("_id"),
        row.get("guid"),
        extra.get("id"),
        extra.get("guid"),
        url,
    )
    if not row_id:
        row_id = hashlib.sha1(f"{title}\n{body}".encode("utf-8")).hexdigest()
    row_id = re.sub(r"[^A-Za-z0-9._\-:]+", "_", row_id)[:180]

    tickers = []
    tickers.extend(extract_tickers_from_value(row.get("tickers")))
    tickers.extend(extract_tickers_from_value(row.get("stocks")))
    tickers.extend(extract_tickers_from_value(extra.get("tickers")))
    tickers.extend(extract_tickers_from_value(extra.get("stocks")))
    ticker_blob = infer_tickers(title=title, body=body, existing=tickers)

    return (
        NormalizedNewsRecord(
            record_id=row_id,
            source=source,
            published_at=published_at,
            doc_date=doc_date,
            title=title,
            body=body,
            ticker=ticker_blob,
            topic=topic,
            url=url,
        ),
        "ok",
    )


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                print(f"[warn] invalid JSONL at {path}:{line_no}", file=sys.stderr)
                continue
            if isinstance(parsed, dict):
                yield parsed


def iter_local_rows(path: Path) -> Iterator[Dict[str, Any]]:
    if path.is_file():
        if path.suffix.lower() != ".jsonl":
            raise RuntimeError(f"Expected .jsonl file: {path}")
        yield from iter_jsonl(path)
        return
    if not path.is_dir():
        raise RuntimeError(f"Input path does not exist: {path}")
    files = sorted(path.rglob("*.jsonl"))
    if not files:
        raise RuntimeError(f"No .jsonl files found under: {path}")
    for file_path in files:
        yield from iter_jsonl(file_path)


def iter_hf_rows(
    dataset_id: str,
    split: str,
    cache_dir: str,
    token_env: str,
    dataset_config: str,
) -> Iterator[Dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        msg = str(exc)
        if "insecure_hashlib" in msg or "huggingface_hub" in msg:
            raise RuntimeError(
                "Incompatible 'datasets' / 'huggingface_hub' versions in your environment. "
                "For this repo's current dependency set, repair with: "
                "financial-engine_v2/.venv/bin/pip install --upgrade "
                "\"huggingface-hub>=0.25,<0.26\""
            ) from exc
        raise RuntimeError("Missing dependency: datasets. Install with: pip install datasets") from exc

    kwargs: Dict[str, Any] = {}
    if cache_dir:
        kwargs["cache_dir"] = cache_dir
    token = os.getenv(token_env.strip()) if token_env.strip() else ""
    if token:
        kwargs["token"] = token

    try:
        if dataset_config.strip():
            ds = load_dataset(dataset_id, dataset_config.strip(), split=split, **kwargs)
        else:
            ds = load_dataset(dataset_id, split=split, **kwargs)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load dataset '{dataset_id}' split='{split}'. "
            "For this gated dataset you may need approved access + HF token, "
            "or use --input-path with local JSONL exports."
        ) from exc

    for row in ds:
        if isinstance(row, dict):
            yield row


def normalize_records(
    rows: Iterable[Dict[str, Any]],
    min_text_chars: int,
    keep_non_english: bool,
    max_rows: int,
) -> Tuple[List[NormalizedNewsRecord], Dict[str, int]]:
    stats: Dict[str, int] = {
        "input_rows": 0,
        "kept_rows": 0,
        "dropped_short_text": 0,
        "dropped_non_english": 0,
        "dropped_duplicate_url": 0,
        "dropped_duplicate_exact": 0,
        "dropped_duplicate_near": 0,
    }

    seen_url_hashes = set()
    seen_exact_hashes = set()
    near_by_title: Dict[str, List[str]] = {}

    out: List[NormalizedNewsRecord] = []
    for row in rows:
        stats["input_rows"] += 1
        if max_rows > 0 and len(out) >= max_rows:
            break

        normalized, reason = normalize_news_row(
            row=row,
            min_text_chars=min_text_chars,
            keep_non_english=keep_non_english,
        )
        if not normalized:
            key = f"dropped_{reason}"
            stats[key] = stats.get(key, 0) + 1
            continue

        if normalized.url:
            url_key = hashlib.sha1(normalized.url.lower().encode("utf-8")).hexdigest()
            if url_key in seen_url_hashes:
                stats["dropped_duplicate_url"] += 1
                continue
            seen_url_hashes.add(url_key)

        exact_key = hashlib.sha1(
            normalize_text_for_dedupe(f"{normalized.title}\n{normalized.body}").encode("utf-8")
        ).hexdigest()
        if exact_key in seen_exact_hashes:
            stats["dropped_duplicate_exact"] += 1
            continue
        seen_exact_hashes.add(exact_key)

        title_key = normalize_text_for_dedupe(normalized.title)[:220]
        body_fp = normalize_text_for_dedupe(normalized.body)[:1800]
        candidates = near_by_title.setdefault(title_key, [])
        is_near_dup = False
        for prev in candidates[-12:]:
            if body_fp[:320] and body_fp[:320] == prev[:320]:
                is_near_dup = True
                break
            if difflib.SequenceMatcher(None, body_fp, prev).ratio() >= 0.95:
                is_near_dup = True
                break
        if is_near_dup:
            stats["dropped_duplicate_near"] += 1
            continue
        candidates.append(body_fp)

        out.append(normalized)

    stats["kept_rows"] = len(out)
    return out, stats


def init_stats() -> Dict[str, int]:
    return {
        "input_rows": 0,
        "kept_rows": 0,
        "dropped_short_text": 0,
        "dropped_non_english": 0,
        "dropped_missing_doc_date": 0,
        "dropped_before_min_doc_date": 0,
        "dropped_after_max_doc_date": 0,
        "dropped_duplicate_url": 0,
        "dropped_duplicate_exact": 0,
        "dropped_duplicate_near": 0,
        "output_chunks": 0,
        "flush_batches": 0,
    }


def dedupe_db_default_path(out_path: Path) -> Path:
    if out_path.suffix:
        return out_path.with_suffix(".dedupe.sqlite")
    return out_path / "news_dedupe.sqlite"


def init_dedupe_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA temp_store=MEMORY")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_url (url_hash TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_exact (exact_hash TEXT PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS seen_near (near_hash TEXT PRIMARY KEY)")
    conn.commit()
    return conn


def near_duplicate_hash(rec: NormalizedNewsRecord) -> str:
    title_key = normalize_text_for_dedupe(rec.title)[:220]
    body_key = normalize_text_for_dedupe(rec.body)
    prefix = body_key[:320]
    token_sig = " ".join(body_key.split()[:80])
    payload = f"{title_key}|{prefix}|{token_sig}".strip("|")
    if not payload:
        return ""
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def dedupe_keep_record(
    rec: NormalizedNewsRecord,
    conn: sqlite3.Connection,
    skip_near_dedupe: bool,
) -> Optional[str]:
    cur = conn.cursor()
    if rec.url:
        url_key = hashlib.sha1(rec.url.lower().encode("utf-8")).hexdigest()
        cur.execute("INSERT OR IGNORE INTO seen_url(url_hash) VALUES (?)", (url_key,))
        if cur.rowcount == 0:
            return "duplicate_url"

    exact_key = hashlib.sha1(
        normalize_text_for_dedupe(f"{rec.title}\n{rec.body}").encode("utf-8")
    ).hexdigest()
    cur.execute("INSERT OR IGNORE INTO seen_exact(exact_hash) VALUES (?)", (exact_key,))
    if cur.rowcount == 0:
        return "duplicate_exact"

    if not skip_near_dedupe:
        near_key = near_duplicate_hash(rec)
        if near_key:
            cur.execute("INSERT OR IGNORE INTO seen_near(near_hash) VALUES (?)", (near_key,))
            if cur.rowcount == 0:
                return "duplicate_near"
    return None


def append_embedding_jsonl(
    records: Sequence[ctx.ChunkRecord],
    vectors: Sequence[Sequence[float]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
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
                "text": rec.text,
                "embedding": list(vec),
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def print_progress(stats: Dict[str, int], started_at: float) -> None:
    elapsed = max(1.0, time.time() - started_at)
    input_rate = stats["input_rows"] / elapsed
    keep_rate = stats["kept_rows"] / elapsed
    print(
        "[progress] "
        f"input={stats['input_rows']:,} kept={stats['kept_rows']:,} "
        f"chunks={stats['output_chunks']:,} batches={stats['flush_batches']:,} "
        f"elapsed_min={elapsed / 60.0:.1f} input_rows_per_sec={input_rate:.1f} "
        f"kept_rows_per_sec={keep_rate:.1f}"
    )


def flush_batch(
    normalized_batch: List[NormalizedNewsRecord],
    args: argparse.Namespace,
    out_path: Path,
    stats: Dict[str, int],
    faiss_records: List[ctx.ChunkRecord],
    faiss_vectors: List[List[float]],
    embedding_jsonl_path: Optional[Path],
) -> int:
    if not normalized_batch:
        return 0
    records = build_chunk_records(
        rows=normalized_batch,
        corpus=args.corpus,
        doc_type=args.doc_type,
        max_chars=max(200, args.max_chars),
        overlap_words=max(0, args.overlap_words),
    )
    normalized_batch.clear()
    if not records:
        return 0

    vectors = ctx.embed_texts(
        [r.text for r in records],
        backend=args.embed_backend,
        model_name=args.embed_model,
        ollama_endpoint=args.ollama_endpoint,
        hash_dim=args.hash_dim,
        st_device=args.st_device,
        st_batch_size=args.st_batch_size,
    )

    if args.db == "sqlite":
        ctx.store_sqlite(records, vectors, out_path)
    elif args.db == "chroma":
        ctx.store_chroma(records, vectors, out_path)
    elif args.db == "faiss":
        faiss_records.extend(records)
        faiss_vectors.extend([list(map(float, v)) for v in vectors])
    else:
        raise AssertionError("Unhandled db backend")

    if embedding_jsonl_path is not None:
        append_embedding_jsonl(records, vectors, embedding_jsonl_path)

    stats["output_chunks"] += len(records)
    stats["flush_batches"] += 1
    return len(records)


def stream_normalize_and_index(
    rows: Iterable[Dict[str, Any]],
    args: argparse.Namespace,
    out_path: Path,
    dedupe_conn: sqlite3.Connection,
    normalized_jsonl_path: Optional[Path],
    embedding_jsonl_path: Optional[Path],
) -> Tuple[Dict[str, int], List[ctx.ChunkRecord], List[List[float]]]:
    stats = init_stats()
    started_at = time.time()
    normalized_batch: List[NormalizedNewsRecord] = []
    faiss_records: List[ctx.ChunkRecord] = []
    faiss_vectors: List[List[float]] = []

    norm_fh = None
    if normalized_jsonl_path is not None:
        normalized_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        norm_fh = normalized_jsonl_path.open("w", encoding="utf-8")

    try:
        for row in rows:
            stats["input_rows"] += 1

            normalized, reason = normalize_news_row(
                row=row,
                min_text_chars=max(1, args.min_text_chars),
                keep_non_english=args.keep_non_english,
            )
            if not normalized:
                stats[f"dropped_{reason}"] = stats.get(f"dropped_{reason}", 0) + 1
                if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                    dedupe_conn.commit()
                    if norm_fh is not None:
                        norm_fh.flush()
                    print_progress(stats, started_at)
                continue

            if args.min_doc_date or args.max_doc_date:
                if not normalized.doc_date:
                    stats["dropped_missing_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue
                if args.min_doc_date and normalized.doc_date < args.min_doc_date:
                    stats["dropped_before_min_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue
                if args.max_doc_date and normalized.doc_date > args.max_doc_date:
                    stats["dropped_after_max_doc_date"] += 1
                    if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                        dedupe_conn.commit()
                        if norm_fh is not None:
                            norm_fh.flush()
                        print_progress(stats, started_at)
                    continue

            dedupe_reason = dedupe_keep_record(
                rec=normalized,
                conn=dedupe_conn,
                skip_near_dedupe=args.skip_near_dedupe,
            )
            if dedupe_reason:
                stats[f"dropped_{dedupe_reason}"] = stats.get(f"dropped_{dedupe_reason}", 0) + 1
                if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                    dedupe_conn.commit()
                    if norm_fh is not None:
                        norm_fh.flush()
                    print_progress(stats, started_at)
                continue

            stats["kept_rows"] += 1
            if norm_fh is not None:
                norm_fh.write(json.dumps(asdict(normalized), ensure_ascii=False) + "\n")
            normalized_batch.append(normalized)

            reached_cap = args.max_rows > 0 and stats["kept_rows"] >= args.max_rows
            should_flush = len(normalized_batch) >= max(1, args.row_batch_size) or reached_cap
            if should_flush:
                flush_batch(
                    normalized_batch=normalized_batch,
                    args=args,
                    out_path=out_path,
                    stats=stats,
                    faiss_records=faiss_records,
                    faiss_vectors=faiss_vectors,
                    embedding_jsonl_path=embedding_jsonl_path,
                )
                dedupe_conn.commit()
                if norm_fh is not None:
                    norm_fh.flush()

            if args.progress_every > 0 and stats["input_rows"] % args.progress_every == 0:
                dedupe_conn.commit()
                if norm_fh is not None:
                    norm_fh.flush()
                print_progress(stats, started_at)

            if reached_cap:
                break

        if normalized_batch:
            flush_batch(
                normalized_batch=normalized_batch,
                args=args,
                out_path=out_path,
                stats=stats,
                faiss_records=faiss_records,
                faiss_vectors=faiss_vectors,
                embedding_jsonl_path=embedding_jsonl_path,
            )
        dedupe_conn.commit()
    finally:
        if norm_fh is not None:
            norm_fh.close()

    print_progress(stats, started_at)
    return stats, faiss_records, faiss_vectors


def build_chunk_records(
    rows: Sequence[NormalizedNewsRecord],
    corpus: str,
    doc_type: str,
    max_chars: int,
    overlap_words: int,
) -> List[ctx.ChunkRecord]:
    out: List[ctx.ChunkRecord] = []
    for rec in rows:
        payload = (f"{rec.title}\n\n{rec.body}" if rec.title else rec.body).strip()
        chunks = ctx.chunk_text(payload, max_chars=max_chars, overlap_words=overlap_words)
        primary_ticker = ctx.parse_ticker_blob(rec.ticker)
        company = primary_ticker[0] if primary_ticker else "NEWS"
        file_ref = rec.url or f"news://{rec.record_id}"
        for idx, chunk in enumerate(chunks):
            digest = hashlib.sha1(chunk.encode("utf-8")).hexdigest()[:12]
            chunk_id = f"{corpus}:{rec.record_id}:{idx}:{digest}"
            out.append(
                ctx.ChunkRecord(
                    chunk_id=chunk_id,
                    company=company,
                    file=file_ref,
                    section="fulltext_context",
                    text=chunk,
                    corpus=corpus,
                    doc_type=doc_type,
                    doc_date=rec.doc_date,
                    source=rec.source,
                    ticker=rec.ticker,
                    topic=rec.topic,
                    url=rec.url,
                    title=rec.title,
                    published_at=rec.published_at,
                )
            )
    return out


def query_after_build(args, out_path: Path, corpus: str) -> None:
    if not args.query:
        return
    if args.db == "sqlite":
        rows = ctx.query_sqlite(
            db_path=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )
    elif args.db == "faiss":
        rows = ctx.query_faiss(
            index_dir=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )
    else:
        rows = ctx.query_chroma(
            chroma_dir=out_path,
            query=args.query,
            backend=args.embed_backend,
            model_name=args.embed_model,
            ollama_endpoint=args.ollama_endpoint,
            hash_dim=args.hash_dim,
            st_device=args.st_device,
            st_batch_size=args.st_batch_size,
            company=args.company_filter,
            corpus_filter=args.corpus_filter or corpus,
            doc_type_filter=args.doc_type_filter,
            date_from=args.date_from,
            date_to=args.date_to,
            top_k=args.top_k,
            ticker_filter=args.ticker_filter,
            source_filter=args.source_filter,
        )

    if not rows:
        print("No retrieval results for that query.")
        return
    for rank, (score, row) in enumerate(rows, start=1):
        print(
            f"\n[{rank}] score={score:.4f} corpus={row.get('corpus','')} "
            f"doc_type={row.get('doc_type','')} source={row.get('source','')} "
            f"ticker={row.get('ticker','')} date={row.get('doc_date','')} "
            f"title={row.get('title','')}"
        )
        print(str(row.get("text", ""))[:600].strip())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build isolated news corpus vector DB (experimental research module)")
    ap.add_argument("--input-path", default="", help="Optional local JSONL file/dir (offline mode)")
    ap.add_argument("--dataset-id", default=DEFAULT_DATASET_ID, help="Hugging Face dataset id")
    ap.add_argument("--dataset-config", default="", help="Optional Hugging Face dataset config name")
    ap.add_argument("--split", default="train", help="Dataset split")
    ap.add_argument("--dataset-cache-dir", default="", help="Hugging Face cache directory")
    ap.add_argument("--hf-token-env", default="HF_TOKEN", help="Env var containing HF token for gated access")
    ap.add_argument("--db", choices=["sqlite", "faiss", "chroma"], default="sqlite", help="Vector storage backend")
    ap.add_argument("--out", default="reports/qual_context/news.sqlite", help="Output DB path")
    ap.add_argument("--normalized-jsonl", default="", help="Optional path to write normalized row JSONL")
    ap.add_argument("--corpus", default="news", help="Corpus label (default: news)")
    ap.add_argument("--doc-type", default="news_article", help="doc_type label (default: news_article)")
    ap.add_argument(
        "--embed-backend",
        choices=["sentence-transformers", "ollama", "hash"],
        default="sentence-transformers",
        help="Embedding runtime",
    )
    ap.add_argument("--embed-model", default="BAAI/bge-large-en-v1.5", help="Embedding model")
    ap.add_argument(
        "--st-device",
        choices=["auto", "cpu", "cuda", "cuda_strict"],
        default="cpu",
        help="Sentence-transformers device",
    )
    ap.add_argument("--st-batch-size", type=int, default=16, help="Sentence-transformers batch size")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--hash-dim", type=int, default=384, help="Vector size for hash embeddings")
    ap.add_argument("--max-chars", type=int, default=1200, help="Chunk size in characters")
    ap.add_argument("--overlap-words", type=int, default=60, help="Chunk overlap in words")
    ap.add_argument("--min-text-chars", type=int, default=200, help="Minimum body length gate")
    ap.add_argument("--min-doc-date", default="", help="Optional inclusive ingest date gate (YYYY-MM-DD)")
    ap.add_argument("--max-doc-date", default="", help="Optional inclusive ingest date gate (YYYY-MM-DD)")
    ap.add_argument("--keep-non-english", action="store_true", help="Disable simple English language gate")
    ap.add_argument("--max-rows", type=int, default=0, help="Optional cap on kept normalized rows")
    ap.add_argument("--row-batch-size", type=int, default=512, help="Normalized row batch size before embed/store flush")
    ap.add_argument("--progress-every", type=int, default=50000, help="Print progress every N input rows (0 disables)")
    ap.add_argument("--dedupe-db", default="", help="Path for persistent dedupe state SQLite")
    ap.add_argument("--reset-dedupe-db", action="store_true", help="Delete existing dedupe DB before run")
    ap.add_argument("--reset-output", action="store_true", help="Delete existing output artifact before run")
    ap.add_argument("--skip-near-dedupe", action="store_true", help="Disable approximate near-duplicate filtering")
    ap.add_argument("--write-embedding-jsonl", action="store_true", help="Also write chunk embeddings JSONL beside SQLite")
    ap.add_argument("--query", default="", help="Optional retrieval query after indexing")
    ap.add_argument("--company-filter", default="", help="Optional company filter for retrieval query")
    ap.add_argument("--corpus-filter", default="", help="Optional corpus filter for retrieval query")
    ap.add_argument("--doc-type-filter", default="news_article", help="Optional doc_type filter for retrieval query")
    ap.add_argument("--ticker-filter", default="", help="Optional ticker filter for retrieval query")
    ap.add_argument("--source-filter", default="", help="Optional source filter for retrieval query")
    ap.add_argument("--date-from", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--date-to", default="", help="Optional inclusive date filter (YYYY-MM-DD)")
    ap.add_argument("--top-k", type=int, default=8, help="Top-k retrieval results")
    ap.add_argument(
        "--research-only-ack",
        action="store_true",
        help="Required flag acknowledging this module is research-only without legal approval",
    )
    args = ap.parse_args()

    if not args.research_only_ack:
        print(COMPLIANCE_NOTICE, file=sys.stderr)
        print("Refusing to run without --research-only-ack.", file=sys.stderr)
        return 2

    print(COMPLIANCE_NOTICE)

    if args.date_from and not ctx.valid_iso_date(args.date_from):
        print(f"Invalid --date-from: {args.date_from}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_to and not ctx.valid_iso_date(args.date_to):
        print(f"Invalid --date-to: {args.date_to}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.date_from and args.date_to and args.date_from > args.date_to:
        print("--date-from cannot be after --date-to.", file=sys.stderr)
        return 2
    if args.min_doc_date and not ctx.valid_iso_date(args.min_doc_date):
        print(f"Invalid --min-doc-date: {args.min_doc_date}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.max_doc_date and not ctx.valid_iso_date(args.max_doc_date):
        print(f"Invalid --max-doc-date: {args.max_doc_date}. Use YYYY-MM-DD.", file=sys.stderr)
        return 2
    if args.min_doc_date and args.max_doc_date and args.min_doc_date > args.max_doc_date:
        print("--min-doc-date cannot be after --max-doc-date.", file=sys.stderr)
        return 2

    out_path = Path(args.out).expanduser()
    if args.db == "sqlite" and out_path.suffix != ".sqlite":
        out_path = out_path / "news.sqlite"

    dedupe_path = Path(args.dedupe_db).expanduser() if args.dedupe_db else dedupe_db_default_path(out_path)
    if args.reset_output:
        if args.db == "sqlite" and out_path.exists():
            out_path.unlink()
        elif args.db in {"faiss", "chroma"} and out_path.exists() and out_path.is_dir():
            shutil.rmtree(out_path)
    if args.reset_dedupe_db and dedupe_path.exists():
        dedupe_path.unlink()
    dedupe_conn = init_dedupe_db(dedupe_path)
    print(f"dedupe_db={dedupe_path}")

    embedding_jsonl_path: Optional[Path] = None
    if args.write_embedding_jsonl:
        if args.db == "sqlite":
            embedding_jsonl_path = out_path.with_suffix(".jsonl")
        else:
            embedding_jsonl_path = out_path / "news_embeddings.jsonl"
        if embedding_jsonl_path.exists():
            embedding_jsonl_path.unlink()

    normalized_jsonl_path: Optional[Path] = None
    if args.normalized_jsonl:
        normalized_jsonl_path = Path(args.normalized_jsonl).expanduser()

    if args.input_path:
        rows_iter = iter_local_rows(Path(args.input_path).expanduser().resolve())
    else:
        rows_iter = iter_hf_rows(
            dataset_id=args.dataset_id,
            split=args.split,
            cache_dir=args.dataset_cache_dir,
            token_env=args.hf_token_env,
            dataset_config=args.dataset_config,
        )

    try:
        stats, faiss_records, faiss_vectors = stream_normalize_and_index(
            rows=rows_iter,
            args=args,
            out_path=out_path,
            dedupe_conn=dedupe_conn,
            normalized_jsonl_path=normalized_jsonl_path,
            embedding_jsonl_path=embedding_jsonl_path,
        )
    finally:
        dedupe_conn.close()

    if stats["kept_rows"] == 0:
        # Keep SQLite schema available even when all rows are filtered out.
        # This avoids downstream "no such table: context_chunks" failures
        # after --reset-output runs that intentionally produce zero records.
        if args.db == "sqlite":
            ctx.store_sqlite([], [], out_path)
        print("No normalized news records remained after quality and dedupe gates.", file=sys.stderr)
        print(json.dumps(stats, indent=2), file=sys.stderr)
        return 1

    if args.db == "sqlite":
        print(f"Stored {stats['output_chunks']} chunks in SQLite: {out_path}")
    elif args.db == "chroma":
        print(f"Stored {stats['output_chunks']} chunks in Chroma dir: {out_path}")
    elif args.db == "faiss":
        if not faiss_records or not faiss_vectors:
            print("No FAISS vectors produced from normalized rows.", file=sys.stderr)
            return 1
        ctx.store_faiss(faiss_records, faiss_vectors, out_path)
        print(f"Stored {len(faiss_records)} chunks in FAISS dir: {out_path}")
    else:
        raise AssertionError("Unhandled db backend")

    print(json.dumps(stats, indent=2))
    query_after_build(args=args, out_path=out_path, corpus=args.corpus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
