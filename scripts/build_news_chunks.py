#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from news_pipeline.chunk_builder import build_news_chunks as run_build_news_chunks  # noqa: E402
from news_pipeline.cli_common import DEFAULT_NEWS_ARTICLES_DB, DEFAULT_NEWS_CONTEXT_DB, parse_provider_list, resolve_path  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build RAG-compatible context_chunks from canonical news articles.")
    ap.add_argument("--from-db", default=str(DEFAULT_NEWS_ARTICLES_DB), help="Canonical news_articles SQLite path")
    ap.add_argument("--to-db", default=str(DEFAULT_NEWS_CONTEXT_DB), help="Target context_chunks SQLite path")
    ap.add_argument("--lane", default="high_precision", choices=["high_precision", "high_recall"], help="Entity-link lane filter")
    ap.add_argument("--from-utc", default="", help="Optional published_at_utc lower bound for chunk refresh")
    ap.add_argument("--to-utc", default="", help="Optional published_at_utc upper bound for chunk refresh")
    ap.add_argument("--max-chars", type=int, default=1200, help="Chunk size in characters")
    ap.add_argument("--overlap-words", type=int, default=60, help="Chunk overlap in words")
    ap.add_argument("--providers", default="", help="Optional comma-separated provider filter")
    ap.add_argument("--embed-backend", default="hash", choices=["hash", "sentence-transformers", "ollama"], help="Embedding backend")
    ap.add_argument("--embed-model", default="BAAI/bge-large-en-v1.5", help="Embedding model")
    ap.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434", help="Ollama endpoint")
    ap.add_argument("--hash-dim", type=int, default=384, help="Hash embedding dimension")
    ap.add_argument("--st-device", default="cpu", choices=["auto", "cpu", "cuda", "cuda_strict"], help="Sentence-transformer device")
    ap.add_argument("--st-batch-size", type=int, default=16, help="Sentence-transformer batch size")
    args = ap.parse_args(argv)

    from_db = resolve_path(args.from_db)
    to_db = resolve_path(args.to_db)
    provider_filter = parse_provider_list(args.providers)

    stats = run_build_news_chunks(
        from_db=from_db,
        to_db=to_db,
        lane=args.lane,
        provider_filter=provider_filter,
        from_utc=args.from_utc,
        to_utc=args.to_utc,
        provider_corpus_map=None,
        max_chars=int(args.max_chars),
        overlap_words=int(args.overlap_words),
        embed_backend=args.embed_backend,
        embed_model=args.embed_model,
        ollama_endpoint=args.ollama_endpoint,
        hash_dim=int(args.hash_dim),
        st_device=args.st_device,
        st_batch_size=int(args.st_batch_size),
    )
    payload = {
        "from_db": str(from_db),
        "to_db": str(to_db),
        "lane": args.lane,
        "from_utc": args.from_utc,
        "to_utc": args.to_utc,
        "provider_filter": provider_filter,
        "stats": stats,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
