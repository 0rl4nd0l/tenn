import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

NEWS = load_module(str(SCRIPTS / "build_news_context_db.py"), "build_news_context_db")


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def load_distinct(db_path: Path, column: str):
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        rows = cur.execute(f"SELECT DISTINCT {column} FROM context_chunks ORDER BY {column}").fetchall()
        return [str(row[0] or "") for row in rows]
    finally:
        conn.close()


class TestAsxOptimisedIngestion(unittest.TestCase):
    def test_asx_optimised_mode_filters_to_au_and_sets_corpus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "gdelt_rows.jsonl"
            out_path = tmp / "news.sqlite"
            allowlist_path = tmp / "asx_allowlist.txt"
            allowlist_path.write_text("AAA\n", encoding="utf-8")

            rows = [
                {
                    "id": "au_keep",
                    "date": "2026-02-20T10:00:00Z",
                    "title": "ASX:AAA shares rally on earnings guidance",
                    "text": (
                        "ASX:AAA shares rallied after earnings and dividend guidance updates. "
                        "Trading volumes remained elevated through the session."
                    )
                    * 4,
                    "source": "example.com.au",
                    "url": "https://example.com.au/markets/a1",
                    "extra_fields": {"domain": "example.com.au"},
                },
                {
                    "id": "non_au_drop",
                    "date": "2026-02-20T11:00:00Z",
                    "title": "ASX:AAA shares rally in offshore coverage",
                    "text": (
                        "ASX:AAA shares were discussed in offshore coverage with no Australian source signals."
                    )
                    * 4,
                    "source": "example.com",
                    "url": "https://example.com/markets/a2",
                    "extra_fields": {"domain": "example.com"},
                },
                {
                    "id": "au_no_entity_drop",
                    "date": "2026-02-20T12:00:00Z",
                    "title": "Australian market snapshot",
                    "text": (
                        "Australian markets were broadly mixed while macro themes dominated discussion."
                    )
                    * 6,
                    "source": "example.com.au",
                    "url": "https://example.com.au/markets/a3",
                    "extra_fields": {"domain": "example.com.au"},
                },
            ]
            write_jsonl(input_path, rows)

            argv = [
                "build_news_context_db.py",
                "--input-path",
                str(input_path),
                "--db",
                "sqlite",
                "--out",
                str(out_path),
                "--embed-backend",
                "hash",
                "--hash-dim",
                "32",
                "--row-batch-size",
                "1",
                "--min-text-chars",
                "20",
                "--ticker-allowlist-path",
                str(allowlist_path),
                "--asx-optimised-mode",
                "--health-json",
                str(tmp / "missing_health.json"),
                "--research-only-ack",
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = NEWS.main()
            self.assertEqual(rc, 0)

            corpora = load_distinct(out_path, "corpus")
            urls = load_distinct(out_path, "url")

            self.assertEqual(corpora, ["news_asx_gdelt"])
            self.assertEqual(urls, ["https://example.com.au/markets/a1"])

    def test_non_asx_mode_preserves_existing_behavior(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            input_path = tmp / "gdelt_rows.jsonl"
            out_path = tmp / "news.sqlite"

            rows = [
                {
                    "id": "au_row",
                    "date": "2026-02-20T10:00:00Z",
                    "title": "ASX:AAA shares rally",
                    "text": "ASX:AAA shares rallied after earnings beat and stronger cash generation." * 5,
                    "source": "example.com.au",
                    "url": "https://example.com.au/markets/a1",
                },
                {
                    "id": "non_au_row",
                    "date": "2026-02-20T11:00:00Z",
                    "title": "Global equities update",
                    "text": "US equities gained after central bank commentary and macro data surprises." * 5,
                    "source": "example.com",
                    "url": "https://example.com/markets/a2",
                },
            ]
            write_jsonl(input_path, rows)

            argv = [
                "build_news_context_db.py",
                "--input-path",
                str(input_path),
                "--db",
                "sqlite",
                "--out",
                str(out_path),
                "--corpus",
                "news_gdelt",
                "--embed-backend",
                "hash",
                "--hash-dim",
                "32",
                "--row-batch-size",
                "1",
                "--min-text-chars",
                "20",
                "--health-json",
                str(tmp / "missing_health.json"),
                "--research-only-ack",
            ]
            with mock.patch.object(sys, "argv", argv):
                rc = NEWS.main()
            self.assertEqual(rc, 0)

            corpora = load_distinct(out_path, "corpus")
            urls = load_distinct(out_path, "url")

            self.assertEqual(corpora, ["news_gdelt"])
            self.assertEqual(urls, ["https://example.com.au/markets/a1", "https://example.com/markets/a2"])


if __name__ == "__main__":
    unittest.main()
