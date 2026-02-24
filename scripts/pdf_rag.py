#!/usr/bin/env python3
import argparse
import importlib.util
import json
import math
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
SOURCE_META_TABLE = "pdf_index_sources"
_CONTEXT_MODULE: Optional[Any] = None


@dataclass
class Chunk:
    file: str
    idx: int
    text: str
    tf: Dict[str, int]


@dataclass(frozen=True)
class PdfFingerprint:
    mtime_ns: int
    size_bytes: int


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(text: str, max_chars: int = 1400, overlap_words: int = 50) -> List[str]:
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


def extract_pdf_text(pdf: Path) -> str:
    try:
        cp = subprocess.run(
            ["pdftotext", str(pdf), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
        )
        return clean_text(cp.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftotext failed for {pdf}: {e.stderr.strip()}") from e


def find_pdfs(root: Path) -> List[Path]:
    return sorted(p for p in root.rglob("*.pdf") if p.is_file())


def build_index(pdf_root: Path) -> Tuple[List[Chunk], Dict[str, float]]:
    chunks: List[Chunk] = []
    pdfs = find_pdfs(pdf_root)
    if not pdfs:
        return chunks, {}
    for pdf in pdfs:
        try:
            txt = extract_pdf_text(pdf)
        except RuntimeError as exc:
            print(f"[warn] {exc}", file=sys.stderr)
            continue
        for idx, ctext in enumerate(chunk_text(txt)):
            tf = Counter(tokenize(ctext))
            if tf:
                chunks.append(Chunk(file=str(pdf), idx=idx, text=ctext, tf=dict(tf)))
    df: Counter = Counter()
    for ch in chunks:
        df.update(ch.tf.keys())
    n = len(chunks) or 1
    idf = {tok: math.log((1 + n) / (1 + freq)) + 1.0 for tok, freq in df.items()}
    return chunks, idf


def score_chunk(chunk: Chunk, q_tf: Dict[str, int], idf: Dict[str, float]) -> float:
    score = 0.0
    for tok, qv in q_tf.items():
        if tok in chunk.tf:
            score += (qv * chunk.tf[tok]) * idf.get(tok, 0.0)
    return score


def retrieve(chunks: List[Chunk], idf: Dict[str, float], query: str, top_k: int) -> List[Tuple[float, Chunk]]:
    q_tf = Counter(tokenize(query))
    scored = [(score_chunk(ch, q_tf, idf), ch) for ch in chunks]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def load_context_module() -> Any:
    global _CONTEXT_MODULE
    if _CONTEXT_MODULE is not None:
        return _CONTEXT_MODULE

    try:
        import build_qualitative_context_db as ctx  # type: ignore

        _CONTEXT_MODULE = ctx
        return ctx
    except Exception:
        pass

    ctx_path = Path(__file__).resolve().with_name("build_qualitative_context_db.py")
    spec = importlib.util.spec_from_file_location("build_qualitative_context_db", str(ctx_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load context module: {ctx_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _CONTEXT_MODULE = module
    return module


def ollama_generate(ollama_endpoint: str, model: str, prompt: str, keep_alive: str) -> str:
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "keep_alive": keep_alive}
    ).encode("utf-8")
    req = urllib.request.Request(
        ollama_endpoint.rstrip("/") + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1800) as r:
            body = json.loads(r.read().decode("utf-8"))
            return body.get("response", "").strip()
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach Ollama API: {e}") from e


def fingerprint_pdf(path: Path) -> PdfFingerprint:
    st = path.stat()
    return PdfFingerprint(mtime_ns=int(st.st_mtime_ns), size_bytes=int(st.st_size))


def current_pdf_fingerprints(pdfs: Sequence[Path]) -> Dict[str, PdfFingerprint]:
    return {str(p): fingerprint_pdf(p) for p in pdfs}


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def ensure_source_meta_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {SOURCE_META_TABLE} (
            file TEXT PRIMARY KEY,
            mtime_ns INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL
        )
        """
    )


def load_source_meta(conn: sqlite3.Connection) -> Dict[str, PdfFingerprint]:
    out: Dict[str, PdfFingerprint] = {}
    if not table_exists(conn, SOURCE_META_TABLE):
        return out
    rows = conn.execute(
        f"SELECT file, mtime_ns, size_bytes FROM {SOURCE_META_TABLE}"
    ).fetchall()
    for row in rows:
        out[str(row[0])] = PdfFingerprint(mtime_ns=int(row[1]), size_bytes=int(row[2]))
    return out


def batched_strings(items: Sequence[str], batch_size: int = 400) -> Iterable[List[str]]:
    if batch_size <= 0:
        batch_size = 400
    values = [str(x) for x in items if str(x).strip()]
    for i in range(0, len(values), batch_size):
        yield values[i : i + batch_size]


def remove_chunk_rows(conn: sqlite3.Connection, files: Sequence[str]) -> None:
    if not files:
        return
    if not table_exists(conn, "context_chunks"):
        return
    for batch in batched_strings(files):
        placeholders = ",".join("?" for _ in batch)
        conn.execute(f"DELETE FROM context_chunks WHERE file IN ({placeholders})", tuple(batch))


def remove_source_meta_rows(conn: sqlite3.Connection, files: Sequence[str]) -> None:
    if not files:
        return
    if not table_exists(conn, SOURCE_META_TABLE):
        return
    for batch in batched_strings(files):
        placeholders = ",".join("?" for _ in batch)
        conn.execute(f"DELETE FROM {SOURCE_META_TABLE} WHERE file IN ({placeholders})", tuple(batch))


def upsert_source_meta_rows(
    conn: sqlite3.Connection,
    fingerprint_map: Dict[str, PdfFingerprint],
    files: Sequence[str],
) -> None:
    rows = []
    for raw in files:
        key = str(raw)
        fp = fingerprint_map.get(key)
        if fp is None:
            continue
        rows.append((key, int(fp.mtime_ns), int(fp.size_bytes)))
    if not rows:
        return
    conn.executemany(
        f"""
        INSERT INTO {SOURCE_META_TABLE}(file, mtime_ns, size_bytes)
        VALUES (?, ?, ?)
        ON CONFLICT(file) DO UPDATE SET
            mtime_ns=excluded.mtime_ns,
            size_bytes=excluded.size_bytes
        """,
        rows,
    )


def collect_spans_for_pdf(
    ctx: Any,
    pdf: Path,
    pdf_root: Path,
    content_scope: str,
    fallback_fulltext: bool,
) -> List[Any]:
    text = extract_pdf_text(pdf)
    company = ctx.derive_company(pdf, pdf_root)
    doc_type = ctx.infer_doc_type(pdf, text)
    doc_date = ctx.infer_doc_date(pdf)

    if content_scope == "targeted":
        spans = ctx.extract_target_sections(pdf, text, company)
        if spans:
            for span in spans:
                span.corpus = "company"
                span.doc_type = doc_type
                span.doc_date = doc_date
            return spans
        if fallback_fulltext:
            return ctx.extract_full_document_span(
                file_path=pdf,
                text=text,
                company=company,
                corpus="company",
                doc_type=doc_type,
                doc_date=doc_date,
            )
        return []

    return ctx.extract_full_document_span(
        file_path=pdf,
        text=text,
        company=company,
        corpus="company",
        doc_type=doc_type,
        doc_date=doc_date,
    )


def sync_vector_store(
    pdf_root: Path,
    db_path: Path,
    rebuild: bool,
    content_scope: str,
    fallback_fulltext: bool,
    max_chars: int,
    overlap_words: int,
    embed_backend: str,
    embed_model: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
) -> Dict[str, int]:
    ctx = load_context_module()
    pdfs = find_pdfs(pdf_root)
    if not pdfs:
        raise RuntimeError(f"No PDFs found in: {pdf_root}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if rebuild and db_path.exists():
        db_path.unlink()

    current = current_pdf_fingerprints(pdfs)
    changed: List[Path]
    removed: List[str]

    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        try:
            ensure_source_meta_table(conn)
            conn.commit()
            stored = load_source_meta(conn)
        finally:
            conn.close()
        changed = sorted(
            [Path(path) for path, fp in current.items() if stored.get(path) != fp],
            key=lambda p: str(p),
        )
        removed = sorted([path for path in stored.keys() if path not in current])
    else:
        changed = list(pdfs)
        removed = []

    if not changed and not removed:
        return {
            "total": len(pdfs),
            "changed": 0,
            "indexed": 0,
            "removed": 0,
            "failed": 0,
            "chunks": 0,
            "skipped": len(pdfs),
        }

    spans: List[Any] = []
    indexed_files: List[Path] = []
    failed_files: List[Path] = []
    for pdf in changed:
        try:
            spans.extend(
                collect_spans_for_pdf(
                    ctx=ctx,
                    pdf=pdf,
                    pdf_root=pdf_root,
                    content_scope=content_scope,
                    fallback_fulltext=fallback_fulltext,
                )
            )
            indexed_files.append(pdf)
        except RuntimeError as exc:
            print(f"[warn] {exc}", file=sys.stderr)
            failed_files.append(pdf)

    records: List[Any] = []
    if spans:
        records = ctx.build_chunk_records(spans, max_chars=max_chars, overlap_words=overlap_words)

    vectors: List[List[float]] = []
    if records:
        vectors = ctx.embed_texts(
            [str(r.text) for r in records],
            backend=embed_backend,
            model_name=embed_model,
            ollama_endpoint=ollama_endpoint,
            hash_dim=hash_dim,
            st_device=st_device,
            st_batch_size=st_batch_size,
        )

    files_to_refresh = [str(p) for p in indexed_files]
    conn = sqlite3.connect(str(db_path))
    try:
        ensure_source_meta_table(conn)
        remove_chunk_rows(conn, removed + files_to_refresh)
        remove_source_meta_rows(conn, removed)
        conn.commit()
    finally:
        conn.close()

    # Always ensure the content table/schema exists, even if this delta produced no rows.
    ctx.store_sqlite(records, vectors, db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_source_meta_table(conn)
        upsert_source_meta_rows(conn, current, files_to_refresh)
        conn.commit()
    finally:
        conn.close()

    return {
        "total": len(pdfs),
        "changed": len(changed),
        "indexed": len(indexed_files),
        "removed": len(removed),
        "failed": len(failed_files),
        "chunks": len(records),
        "skipped": max(0, len(pdfs) - len(changed)),
    }


def retrieve_vector(
    db_path: Path,
    query: str,
    top_k: int,
    embed_backend: str,
    embed_model: str,
    ollama_endpoint: str,
    hash_dim: int,
    st_device: str,
    st_batch_size: int,
    company: str,
) -> List[Tuple[float, Dict[str, str]]]:
    if not db_path.exists():
        return []
    ctx = load_context_module()
    return ctx.query_sqlite(
        db_path=db_path,
        query=query,
        backend=embed_backend,
        model_name=embed_model,
        ollama_endpoint=ollama_endpoint,
        hash_dim=hash_dim,
        st_device=st_device,
        st_batch_size=st_batch_size,
        company=company,
        corpus_filter="company",
        doc_type_filter="",
        date_from="",
        date_to="",
        top_k=top_k,
        ticker_filter="",
        source_filter="",
        exclude_corpus_filter="",
    )


def build_lexical_context(pdf_dir: Path, query: str, top_k: int) -> str:
    chunks, idf = build_index(pdf_dir)
    if not chunks:
        return ""
    hits = retrieve(chunks, idf, query, top_k)
    if not hits:
        return ""
    parts = [f"[Chunk {rank}] {ch.file}#{ch.idx}\n{ch.text}" for rank, (_, ch) in enumerate(hits, start=1)]
    return "\n\n".join(parts)


def build_vector_context(hits: Sequence[Tuple[float, Dict[str, str]]]) -> str:
    parts: List[str] = []
    for rank, (score, row) in enumerate(hits, start=1):
        file_path = str(row.get("file", ""))
        section = str(row.get("section", ""))
        chunk_id = str(row.get("chunk_id", ""))
        text = str(row.get("text", ""))
        label = chunk_id or section or "chunk"
        parts.append(f"[Chunk {rank}] score={score:.4f} {file_path}#{label}\n{text}")
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Local PDF RAG with persistent vector retrieval")
    ap.add_argument("--pdf-dir", default="docs", help="Directory containing PDFs")
    ap.add_argument("--retriever", choices=["vector", "lexical"], default="vector", help="Retrieval mode")
    ap.add_argument(
        "--vector-db",
        default="reports/qual_context/pdf_rag.sqlite",
        help="SQLite vector DB path",
    )
    ap.add_argument("--rebuild-index", action="store_true", help="Force full vector index rebuild")
    ap.add_argument("--no-index-sync", action="store_true", help="Do not update vector index before querying")
    ap.add_argument(
        "--content-scope",
        choices=["fulltext", "targeted"],
        default="fulltext",
        help="Indexed content scope for vector mode",
    )
    ap.add_argument(
        "--fallback-fulltext",
        action="store_true",
        help="When targeted indexing finds no target headings, index full document instead",
    )
    ap.add_argument("--max-chars", type=int, default=1200, help="Max chunk size in characters")
    ap.add_argument("--overlap-words", type=int, default=60, help="Chunk overlap in words")
    ap.add_argument(
        "--embed-backend",
        choices=["sentence-transformers", "ollama", "hash"],
        default="ollama",
        help="Embedding runtime for vector retrieval",
    )
    ap.add_argument("--embed-model", default="nomic-embed-text", help="Embedding model name")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama base URL")
    ap.add_argument("--hash-dim", type=int, default=384, help="Vector size for hash embeddings")
    ap.add_argument(
        "--st-device",
        choices=["auto", "cpu", "cuda", "cuda_strict"],
        default="auto",
        help="Device for sentence-transformers embeddings",
    )
    ap.add_argument("--st-batch-size", type=int, default=16, help="Batch size for sentence-transformers encode")
    ap.add_argument("--company", default="", help="Optional company/ticker filter for vector retrieval")
    ap.add_argument("--model", default="qwen2.5:32b", help="Ollama generation model name")
    ap.add_argument("--top-k", type=int, default=6, help="Number of chunks to retrieve")
    ap.add_argument("--keep-alive", default="2h", help="Ollama keep_alive value")
    ap.add_argument("--no-lexical-fallback", action="store_true", help="Disable lexical fallback if vector hits are empty")
    ap.add_argument("--dry-run", action="store_true", help="Show retrieved context only")
    ap.add_argument("query", help="Question to ask")
    args = ap.parse_args()

    if shutil.which("pdftotext") is None:
        print("Missing dependency: pdftotext. Install: sudo apt install -y poppler-utils", file=sys.stderr)
        return 2

    pdf_dir = Path(args.pdf_dir).resolve()
    if not pdf_dir.exists():
        print(f"PDF directory not found: {pdf_dir}", file=sys.stderr)
        return 2

    context = ""
    if args.retriever == "vector":
        db_path = Path(args.vector_db).resolve()
        if args.no_index_sync:
            if not db_path.exists():
                print(f"Vector DB not found (index sync disabled): {db_path}", file=sys.stderr)
                return 2
        else:
            try:
                stats = sync_vector_store(
                    pdf_root=pdf_dir,
                    db_path=db_path,
                    rebuild=bool(args.rebuild_index),
                    content_scope=args.content_scope,
                    fallback_fulltext=bool(args.fallback_fulltext),
                    max_chars=int(args.max_chars),
                    overlap_words=int(args.overlap_words),
                    embed_backend=args.embed_backend,
                    embed_model=args.embed_model,
                    ollama_endpoint=args.ollama_endpoint,
                    hash_dim=int(args.hash_dim),
                    st_device=args.st_device,
                    st_batch_size=int(args.st_batch_size),
                )
                print(
                    "[index] "
                    f"total={stats['total']} changed={stats['changed']} indexed={stats['indexed']} "
                    f"removed={stats['removed']} failed={stats['failed']} skipped={stats['skipped']} "
                    f"chunks={stats['chunks']}",
                    file=sys.stderr,
                )
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 2

        try:
            hits = retrieve_vector(
                db_path=db_path,
                query=args.query,
                top_k=int(args.top_k),
                embed_backend=args.embed_backend,
                embed_model=args.embed_model,
                ollama_endpoint=args.ollama_endpoint,
                hash_dim=int(args.hash_dim),
                st_device=args.st_device,
                st_batch_size=int(args.st_batch_size),
                company=args.company,
            )
        except Exception as exc:
            print(f"[warn] vector retrieval failed: {exc}", file=sys.stderr)
            hits = []

        if hits:
            context = build_vector_context(hits)
        elif not args.no_lexical_fallback:
            print("[warn] No vector hits; falling back to lexical retrieval.", file=sys.stderr)
            context = build_lexical_context(pdf_dir, args.query, int(args.top_k))
    else:
        context = build_lexical_context(pdf_dir, args.query, int(args.top_k))

    if not context:
        print("No relevant chunks found for that query.")
        return 1

    if args.dry_run:
        print(context)
        return 0

    prompt = (
        "Answer using only the provided context.\n"
        "If the context is insufficient, say exactly what is missing.\n\n"
        f"Question: {args.query}\n\n"
        f"Context:\n{context}"
    )
    try:
        answer = ollama_generate(args.ollama_endpoint, args.model, prompt, args.keep_alive)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
