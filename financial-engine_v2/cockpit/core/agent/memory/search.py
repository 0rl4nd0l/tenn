"""MemorySearch — optional SQLite-vec semantic search over memory files.

Gracefully degrades to no-op if sqlite-vec is not installed.

Usage::

    from cockpit.core.agent.memory.search import MemorySearch

    search = MemorySearch(db_path=Path("~/.tenn/memory/memory.db"))
    search.index("BHP revenue: $55B", source="research/BHP")
    results = search.query("BHP revenue", top_k=3)
    # [{"source": "research/BHP", "content": "BHP revenue: $55B", "score": 0.95}]

Implementation note — sqlite-vec vec0 DELETE limitation:
    sqlite-vec's ``vec0`` virtual table (v0.1.x) does **not** honour
    ``DELETE ... WHERE <non-rowid column>`` or even ``DELETE ... WHERE rowid = ?``
    when the rowid is read back from the virtual table itself.  The only
    reliable way to delete a specific row is to track the internal rowid at
    insert time in a separate metadata table, then issue
    ``DELETE FROM memory_chunks WHERE rowid = <tracked_rowid>``.
    A companion table ``memory_chunks_meta`` stores this mapping.
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
                    embedding FLOAT[{self.dims}]
                )
                """
            )
            # Companion metadata table: maps source + text to the vec0 internal rowid.
            # Required because vec0 DELETE only works when targeting the exact internal
            # rowid obtained at INSERT time (see module docstring).
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_chunks_meta (
                    id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    rowid   INTEGER NOT NULL,
                    source  TEXT NOT NULL,
                    text    TEXT NOT NULL
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
        Uses the companion ``memory_chunks_meta`` table to reliably track
        the vec0 internal rowid for deletion (see module-level docstring).
        """
        if not self._available:
            return
        embedding = self.embed_fn(text)
        blob = _float_list_to_bytes(embedding)
        conn = self._connect()
        self._load_vec(conn)

        # Delete any existing rows for this source via tracked rowids.
        existing = conn.execute(
            "SELECT rowid FROM memory_chunks_meta WHERE source = ?", (source,)
        ).fetchall()
        for meta_row in existing:
            vec_rowid = meta_row["rowid"]
            conn.execute("DELETE FROM memory_chunks WHERE rowid = ?", (vec_rowid,))
        conn.execute(
            "DELETE FROM memory_chunks_meta WHERE source = ?", (source,)
        )

        # Insert new vector row and record its internal rowid.
        cur = conn.execute(
            "INSERT INTO memory_chunks(embedding) VALUES (?)",
            (blob,),
        )
        vec_rowid = cur.lastrowid
        conn.execute(
            "INSERT INTO memory_chunks_meta(rowid, source, text) VALUES (?, ?, ?)",
            (vec_rowid, source, text),
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
        Each result is a dict with keys ``source``, ``content``, and ``score``.
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
                SELECT m.source, m.text, v.distance
                FROM memory_chunks v
                JOIN memory_chunks_meta m ON m.rowid = v.rowid
                WHERE v.embedding MATCH ?
                  AND k = ?
                ORDER BY v.distance
                """,
                (blob, top_k),
            ).fetchall()
            conn.close()
            return [
                {
                    "source": row["source"],
                    "content": row["text"],
                    "score": 1.0 - float(row["distance"]),
                }
                for row in rows
            ]
        except Exception:  # noqa: BLE001
            return []
