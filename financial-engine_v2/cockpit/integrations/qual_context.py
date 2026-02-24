from __future__ import annotations

import importlib.util
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class QualContextReader:
    """Thin wrapper around scripts/build_qualitative_context_db.py query_sqlite().

    Cockpit itself does not implement vector retrieval. This adapter lets Cockpit
    reuse the existing qualitative context SQLite store (and its embedding
    backend) when available.
    """

    CACHE_TTL_SECONDS = 30.0
    MAX_CACHE = 64

    def __init__(
        self,
        repo_root: Path,
        *,
        db_path: str,
        embed_backend: str = "sentence-transformers",
        embed_model: str = "bge-large-en-v1.5",
        corpus_filter: str = "company",
        exclude_corpus_filter: str = "",
        top_k: int = 8,
        max_text_chars: int = 1200,
        ollama_endpoint: str = "http://127.0.0.1:11434",
        hash_dim: int = 384,
        st_device: str = "auto",
        st_batch_size: int = 16,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.db_path = str(Path(db_path).expanduser())
        self.embed_backend = str(embed_backend or "sentence-transformers").strip()
        self.embed_model = str(embed_model or "bge-large-en-v1.5").strip()
        self.corpus_filter = str(corpus_filter or "").strip()
        self.exclude_corpus_filter = str(exclude_corpus_filter or "").strip()
        self.top_k = int(max(1, top_k))
        self.max_text_chars = int(max(200, max_text_chars))
        self.ollama_endpoint = str(ollama_endpoint or "http://127.0.0.1:11434").strip()
        self.hash_dim = int(max(8, hash_dim))
        self.st_device = str(st_device or "auto").strip()
        self.st_batch_size = int(max(1, st_batch_size))

        self._module: Any | None = None
        self._cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        self._db_embedding_dim: int | None = None

    def validate_runtime(self) -> None:
        db_path = Path(self.db_path).expanduser().resolve()
        if not db_path.exists() or not db_path.is_file():
            raise FileNotFoundError(f"qual context db not found: {db_path}")

        # Ensure retrieval script can be loaded before first query.
        self._load_module()
        self._validate_embedding_backend()
        self._validate_hash_embedding_compatibility(db_path)

    def _validate_embedding_backend(self) -> None:
        backend = str(self.embed_backend or "").strip().lower()
        if backend not in {"sentence-transformers", "hash", "ollama"}:
            raise ValueError(
                f"Unsupported RAG embed backend '{self.embed_backend}'. "
                "Expected one of: sentence-transformers, hash, ollama."
            )
        if backend == "sentence-transformers":
            try:
                import sentence_transformers  # type: ignore # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "RAG embed backend 'sentence-transformers' is configured but dependency is missing. "
                    "Install with: pip install sentence-transformers"
                ) from exc
            st_mode = str(self.st_device or "auto").strip().lower()
            if st_mode in {"cuda_strict", "strict_cuda"}:
                try:
                    import torch  # type: ignore
                except Exception as exc:
                    raise RuntimeError(
                        "RAG CUDA strict mode requested but PyTorch is unavailable in this environment."
                    ) from exc
                if not torch.cuda.is_available() or int(torch.cuda.device_count()) <= 0:
                    raise RuntimeError(
                        "RAG CUDA strict mode requested (st_device=cuda_strict) but no CUDA GPU is visible to PyTorch."
                    )

    def _read_db_embedding_dim(self, db_path: Path) -> int | None:
        if self._db_embedding_dim is not None:
            return self._db_embedding_dim
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            row = cur.execute("SELECT embedding_json FROM context_chunks LIMIT 1").fetchone()
        except Exception:
            return None
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        if not row or not row[0]:
            return None
        try:
            vec = json.loads(str(row[0]))
        except Exception:
            return None
        if not isinstance(vec, list):
            return None
        dim = len(vec)
        if dim <= 0:
            return None
        self._db_embedding_dim = int(dim)
        return self._db_embedding_dim

    def _validate_hash_embedding_compatibility(self, db_path: Path) -> None:
        backend = str(self.embed_backend or "").strip().lower()
        if backend != "hash":
            return
        db_dim = self._read_db_embedding_dim(db_path)
        if db_dim is None:
            return
        if db_dim != self.hash_dim:
            raise RuntimeError(
                "RAG hash embedding dimension mismatch: "
                f"db_dim={db_dim}, hash_dim={self.hash_dim}. "
                "Rebuild the qualitative context DB with matching hash_dim or use the backend used to build the DB."
            )

    def _load_module(self) -> Any:
        if self._module is not None:
            return self._module
        candidates = [
            (self.repo_root / "scripts" / "build_qualitative_context_db.py").resolve(),
            (self.repo_root.parent / "scripts" / "build_qualitative_context_db.py").resolve(),
            (Path.cwd() / "scripts" / "build_qualitative_context_db.py").resolve(),
        ]
        script_path = next((path for path in candidates if path.exists() and path.is_file()), None)
        if script_path is None:
            raise FileNotFoundError(
                "Qual context script not found in expected locations: "
                + ", ".join(str(path) for path in candidates)
            )
        spec = importlib.util.spec_from_file_location("build_qualitative_context_db", str(script_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module spec: {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module = module
        return module

    def query(
        self,
        *,
        query: str,
        company: str,
        deep_mode: bool,
        top_k: int | None = None,
        doc_type_filter: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> dict[str, Any]:
        q = str(query or "").strip()
        comp = str(company or "").strip().upper()
        limit = int(top_k) if top_k is not None else self.top_k
        limit = int(max(1, limit))
        doc_type = str(doc_type_filter or "").strip()
        start_date = str(date_from or "").strip()
        end_date = str(date_to or "").strip()
        deep_flag = bool(deep_mode)

        cache_key = (comp, q, limit, doc_type, start_date, end_date, deep_flag)
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] <= self.CACHE_TTL_SECONDS:
            return cached[1]

        payload: dict[str, Any] = {
            "ok": False,
            "query": q,
            "company": comp,
            "db_path": self.db_path,
            "embed_backend": self.embed_backend,
            "embed_model": self.embed_model,
            "corpus_filter": self.corpus_filter,
            "exclude_corpus_filter": self.exclude_corpus_filter,
            "doc_type_filter": doc_type,
            "date_from": start_date,
            "date_to": end_date,
            "top_k": limit,
            "deep_mode": deep_flag,
            "hits": [],
            "error": None,
        }

        db_path = Path(self.db_path).expanduser().resolve()
        if not db_path.exists() or not db_path.is_file():
            payload["error"] = f"qual context db not found: {db_path}"
            return payload

        if not q or not comp:
            payload["error"] = "query and company are required"
            return payload

        try:
            mod = self._load_module()
            self._validate_hash_embedding_compatibility(db_path)
            rows = mod.query_sqlite(
                db_path=db_path,
                query=q,
                backend=self.embed_backend,
                model_name=self.embed_model,
                ollama_endpoint=self.ollama_endpoint,
                hash_dim=self.hash_dim,
                st_device=self.st_device,
                st_batch_size=self.st_batch_size,
                company=comp,
                corpus_filter=self.corpus_filter,
                doc_type_filter=doc_type,
                date_from=start_date,
                date_to=end_date,
                top_k=limit,
                ticker_filter="",
                source_filter="",
                exclude_corpus_filter=self.exclude_corpus_filter,
            )
            hits: list[dict[str, Any]] = []
            for score, row in rows:
                if not isinstance(row, dict):
                    continue
                text = str(row.get("text") or "")
                excerpt_chars = 2800 if deep_flag else self.max_text_chars
                hits.append(
                    {
                        "score": float(score),
                        "company": row.get("company"),
                        "corpus": row.get("corpus"),
                        "doc_type": row.get("doc_type"),
                        "doc_date": row.get("doc_date"),
                        "file": row.get("file"),
                        "section": row.get("section"),
                        "title": row.get("title"),
                        "published_at": row.get("published_at"),
                        "text": text[:excerpt_chars],
                    }
                )
            payload["hits"] = hits
            payload["ok"] = True
        except Exception as exc:
            payload["error"] = str(exc)[:400]

        if len(self._cache) >= self.MAX_CACHE:
            oldest_key = min(self._cache.items(), key=lambda item: item[1][0])[0]
            self._cache.pop(oldest_key, None)
        self._cache[cache_key] = (now, payload)
        return payload
