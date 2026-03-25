"""MemorySearch — optional SQLite-vec semantic search over memory files.

Gracefully degrades to no-op if sqlite-vec is not installed.

Usage::

    from cockpit.core.agent.memory.search import MemorySearch

    search = MemorySearch(db_path=Path("~/.tenn/memory/memory.db"))
    search.index("BHP revenue: $55B", source="research/BHP")
    results = search.query("BHP revenue", top_k=3)
    # [{"source": "research/BHP", "text": "BHP revenue: $55B", "distance": 0.0}]
"""
from __future__ import annotations

import struct
import sqlite3
from pathlib import Path
from typing import Callable, Any

_DEFAULT_DIMS = 768  # nomic-embed-text output dimension


def _float_list_to_bytes(values: list[float]) -> bytes:
    """Pack a list of floats into a little-endian binary blob for sqlite-vec."""
    return struct.pack(f"{len(values)}f", *values)


def _default_embed(text: str) -> list[float]:
    """Default embed function — calls Ollama nomic-embed-text.

    This is the production path. Inject a stub via *embed_fn* in tests.
    """
    try:
        import httpx  # type: ignore

        resp = httpx.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Ollama embed failed: {exc}") from exc


class MemorySearch:
    """SQLite-vec backed semantic search over memory chunks.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file (created if absent).
    embed_fn:
        Callable that maps a text string to a float list embedding.
        Defaults to Ollama nomic-embed-text.
    dims:
        Embedding dimensionality. Must match *embed_fn* output.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        embed_fn: Callable[[str], list[float]] | None = None,
        dims: int = _DEFAULT_DIMS,
    ) -> None:
        self.db_path = Path(db_path) if db_path is not None else Path.home() / ".tenn" / "memory" / "memory.db"
        self.embed_fn = embed_fn or _default_embed
        self.dims = dims
        self._available = False  # set True once DB is ready

        self._init_db()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create/open the DB and load the sqlite-vec extension."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import sqlite_vec  # type: ignore  # noqa: F401

            conn = self._connect()
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)

            conn.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_chunks USING vec0(
                    source TEXT,
                    text TEXT,
                    embedding FLOAT[{self.dims}]
                )
                """
            )
            conn.commit()
            conn.close()
            self._available = True
        except (ImportError, Exception):  # noqa: BLE001
            # sqlite-vec not installed or failed to load — degrade gracefully
            self._available = False

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _load_vec(self, conn: sqlite3.Connection) -> None:
        """Load the sqlite-vec extension into *conn*."""
        import sqlite_vec  # type: ignore

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def index(self, text: str, source: str) -> None:
        """Embed *text* and insert a chunk into the vector index.

        If a row with the same *source* already exists, it is replaced.
        """
        if not self._available:
            return
        embedding = self.embed_fn(text)
        blob = _float_list_to_bytes(embedding)
        conn = self._connect()
        self._load_vec(conn)
        # Delete any existing row for this source before inserting
        conn.execute("DELETE FROM memory_chunks WHERE source = ?", (source,))
        conn.execute(
            "INSERT INTO memory_chunks(source, text, embedding) VALUES (?, ?, ?)",
            (source, text, blob),
        )
        conn.commit()
        conn.close()

    def reindex_source(self, source: str, new_text: str) -> None:
        """Delete all chunks for *source* and re-index with *new_text*."""
        if not self._available:
            return
        self.index(new_text, source)

    def query(self, text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Return the *top_k* most similar chunks to *text*.

        Returns an empty list if sqlite-vec is unavailable or the index is empty.
        Each result is a dict with keys ``source``, ``text``, and ``distance``.
        """
        if not self._available:
            return []
        try:
            embedding = self.embed_fn(text)
            blob = _float_list_to_bytes(embedding)
            conn = self._connect()
            self._load_vec(conn)
            rows = conn.execute(
                """
                SELECT source, text, distance
                FROM memory_chunks
                WHERE embedding MATCH ?
                  AND k = ?
                ORDER BY distance
                """,
                (blob, top_k),
            ).fetchall()
            conn.close()
            return [{"source": row["source"], "content": row["text"], "score": 1.0 - float(row["distance"])} for row in rows]
        except Exception:  # noqa: BLE001
            return []
