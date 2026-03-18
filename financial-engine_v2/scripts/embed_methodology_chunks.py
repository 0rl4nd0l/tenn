#!/usr/bin/env python3
"""Stage 3 embedding/indexing for methodology chunks."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_SEMANTIC_CHUNKS = WORKSPACE_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl"
DEFAULT_COLLECTION = "methodology_chunks"


def _ensure_backend_path() -> None:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))


def _load_backend_embedding_runtime() -> dict[str, Any]:
    _ensure_backend_path()
    try:
        import httpx
        from qdrant_client import QdrantClient

        from app.core.config import settings
        from app.services.embeddings import ensure_collection, upsert_points
        from app.services.ollama import ollama_embed
    except ImportError as exc:
        raise RuntimeError(
            "Embedding runtime dependencies are unavailable. "
            "Use the financial-engine_v2 environment with backend dependencies installed."
        ) from exc

    return {
        "httpx": httpx,
        "QdrantClient": QdrantClient,
        "settings": settings,
        "ensure_collection": ensure_collection,
        "upsert_points": upsert_points,
        "ollama_embed": ollama_embed,
    }


@dataclass(frozen=True)
class ChunkRow:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    source_file: str
    page_start: int | None
    page_end: int | None
    framework_family: str
    section: str


def _coerce_optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _resolve_semantic_chunks_path(path: Path) -> Path:
    requested = path.expanduser().resolve()
    candidates = [requested]

    if requested.name == "semantic_chunks.jsonl":
        candidates.extend(
            [
                WORKSPACE_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl",
                REPO_ROOT / "reports" / "investment_preprocess" / "semantic_chunks.jsonl",
            ]
        )

    checked: list[Path] = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        checked.append(resolved)
        if resolved.exists():
            return resolved

    checked_str = "\n".join(f"- {candidate}" for candidate in checked)
    raise FileNotFoundError(
        "semantic chunks file not found. Checked:\n"
        f"{checked_str}\n"
        "Run stage 1+2 first with `preprocess_investment_pdfs.py`, or pass the correct `--semantic-chunks` path."
    )


def _load_chunk_rows(path: Path) -> list[ChunkRow]:
    rows: list[ChunkRow] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"semantic chunk row {lineno} is not a JSON object")
            doc_id = str(payload.get("doc_id") or "").strip()
            chunk_index_raw = payload.get("chunk_index")
            chunk_id = str(payload.get("chunk_id") or "").strip()
            chunk_text = str(payload.get("text") or "").strip()
            if not doc_id:
                raise RuntimeError(f"semantic chunk row {lineno} is missing doc_id")
            if chunk_index_raw in (None, ""):
                raise RuntimeError(f"semantic chunk row {lineno} is missing chunk_index")
            if not chunk_id:
                raise RuntimeError(f"semantic chunk row {lineno} is missing chunk_id")
            if not chunk_text:
                raise RuntimeError(f"semantic chunk row {lineno} is missing text")
            rows.append(
                ChunkRow(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    chunk_index=int(chunk_index_raw),
                    text=chunk_text,
                    source_file=str(payload.get("source_file_name") or payload.get("source_file") or "").strip(),
                    page_start=_coerce_optional_int(payload.get("page_start")),
                    page_end=_coerce_optional_int(payload.get("page_end")),
                    framework_family=str(payload.get("framework_family") or "unknown").strip() or "unknown",
                    section=str(payload.get("section") or "").strip(),
                )
            )
    return rows


def _default_embed_batch(
    texts: Sequence[str],
    *,
    ollama_url: str,
    model: str,
    client: Any = None,
    backend_runtime: dict[str, Any],
) -> list[list[float]]:
    return backend_runtime["ollama_embed"](ollama_url, model, list(texts), client=client)


def _logical_point_id(row: ChunkRow) -> str:
    return f"{row.doc_id}:{row.chunk_index}"


def _qdrant_point_id(logical_point_id: str) -> str:
    # Remote Qdrant accepts integer or UUID point IDs. Preserve the logical ID
    # separately and use a deterministic UUID for storage.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"methodology_chunks:{logical_point_id}"))


def _build_payload(row: ChunkRow, logical_point_id: str) -> dict[str, Any]:
    return {
        "logical_point_id": logical_point_id,
        "chunk_id": row.chunk_id,
        "source_file": row.source_file,
        "page_start": row.page_start,
        "page_end": row.page_end,
        "framework_family": row.framework_family,
        "section": row.section,
    }


def run(
    semantic_chunks_path: Path,
    out_dir: Path | None = None,
    *,
    collection: str = DEFAULT_COLLECTION,
    batch_size: int | None = None,
    qdrant_url: str = "",
    ollama_url: str = "",
    embed_model: str = "",
    embed_batch_fn: Callable[..., list[list[float]]] | None = None,
    qdrant_factory: Callable[[str], Any] | None = None,
    ensure_collection_fn: Callable[[Any, str, int], None] | None = None,
    upsert_points_fn: Callable[[Any, str, list[dict[str, Any]]], None] | None = None,
) -> dict[str, Any]:
    semantic_chunks_path = _resolve_semantic_chunks_path(semantic_chunks_path)

    backend_runtime = _load_backend_embedding_runtime()
    settings = backend_runtime["settings"]

    out_dir = (out_dir or (semantic_chunks_path.parent / "embeddings")).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "embedding_manifest.jsonl"
    summary_path = out_dir / "run_summary.json"

    rows = _load_chunk_rows(semantic_chunks_path)
    if not rows:
        _write_jsonl(manifest_path, [])
        summary = {
            "status": "success",
            "semantic_chunks": str(semantic_chunks_path),
            "out_dir": str(out_dir),
            "collection": collection,
            "chunks_embedded": 0,
            "embedding_dim": 0,
            "manifest_files": {"embedding_manifest": str(manifest_path)},
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    resolved_batch_size = max(1, int(batch_size or getattr(settings, "embedding_batch_size", 32) or 32))
    resolved_qdrant_url = str(qdrant_url or getattr(settings, "qdrant_url", "")).strip()
    resolved_ollama_url = str(ollama_url or getattr(settings, "ollama_url", "")).strip()
    resolved_embed_model = str(embed_model or getattr(settings, "embed_model", "")).strip()
    if not resolved_qdrant_url:
        raise RuntimeError("qdrant_url is required")
    if not resolved_ollama_url:
        raise RuntimeError("ollama_url is required")
    if not resolved_embed_model:
        raise RuntimeError("embed_model is required")

    qdrant_factory = qdrant_factory or backend_runtime["QdrantClient"]
    ensure_collection_fn = ensure_collection_fn or backend_runtime["ensure_collection"]
    upsert_points_fn = upsert_points_fn or backend_runtime["upsert_points"]
    embed_batch_fn = embed_batch_fn or _default_embed_batch

    client = None
    http_client = None
    try:
        http_client = backend_runtime["httpx"].Client(timeout=180.0)
        client = qdrant_factory(resolved_qdrant_url)
        manifest_rows: list[dict[str, Any]] = []
        vector_dim = 0
        for start in range(0, len(rows), resolved_batch_size):
            batch_rows = rows[start : start + resolved_batch_size]
            batch_texts = [row.text for row in batch_rows]
            batch_vectors = embed_batch_fn(
                batch_texts,
                ollama_url=resolved_ollama_url,
                model=resolved_embed_model,
                client=http_client,
                backend_runtime=backend_runtime,
            )
            if len(batch_vectors) != len(batch_rows):
                raise RuntimeError(
                    f"embedding batch size mismatch: expected {len(batch_rows)}, got {len(batch_vectors)}"
                )
            if batch_vectors:
                vector_dim = len(batch_vectors[0])
                ensure_collection_fn(client, collection, vector_dim)
            points: list[dict[str, Any]] = []
            for row, vector in zip(batch_rows, batch_vectors):
                logical_point_id = _logical_point_id(row)
                qdrant_point_id = _qdrant_point_id(logical_point_id)
                payload = _build_payload(row, logical_point_id)
                points.append({"id": qdrant_point_id, "vector": list(vector), "payload": payload})
                manifest_rows.append(
                    {
                        "point_id": logical_point_id,
                        "qdrant_point_id": qdrant_point_id,
                        "chunk_id": row.chunk_id,
                        "doc_id": row.doc_id,
                        "chunk_index": row.chunk_index,
                        "embedding_dim": len(vector),
                        "payload": payload,
                    }
                )
            if points:
                upsert_points_fn(client, collection, points)
    finally:
        if http_client is not None:
            http_client.close()

    _write_jsonl(manifest_path, manifest_rows)
    summary = {
        "status": "success",
        "semantic_chunks": str(semantic_chunks_path),
        "out_dir": str(out_dir),
        "collection": collection,
        "chunks_embedded": len(rows),
        "embedding_dim": manifest_rows[0]["embedding_dim"] if manifest_rows else 0,
        "batch_size": resolved_batch_size,
        "ollama_url": resolved_ollama_url,
        "embed_model": resolved_embed_model,
        "qdrant_url": resolved_qdrant_url,
        "manifest_files": {"embedding_manifest": str(manifest_path)},
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed methodology semantic chunks and upsert them into Qdrant.")
    parser.add_argument(
        "--semantic-chunks",
        default=str(DEFAULT_SEMANTIC_CHUNKS),
        help="Path to semantic_chunks.jsonl from stage 2 preprocessing.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help="Output directory for embedding artifacts. Defaults to <semantic-chunks-parent>/embeddings.",
    )
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="Qdrant collection name.")
    parser.add_argument("--batch-size", type=int, default=0, help="Embedding batch size. Defaults to backend config.")
    parser.add_argument("--qdrant-url", default="", help="Qdrant URL. Defaults to backend config.")
    parser.add_argument("--ollama-url", default="", help="Ollama URL. Defaults to backend config.")
    parser.add_argument("--embed-model", default="", help="Embedding model. Defaults to backend config.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run(
        semantic_chunks_path=Path(args.semantic_chunks),
        out_dir=Path(args.out_dir).expanduser().resolve() if args.out_dir else None,
        collection=str(args.collection),
        batch_size=int(args.batch_size) if int(args.batch_size or 0) > 0 else None,
        qdrant_url=str(args.qdrant_url),
        ollama_url=str(args.ollama_url),
        embed_model=str(args.embed_model),
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
