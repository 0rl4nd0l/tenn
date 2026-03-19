import importlib
import importlib.util
import gzip
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
DB = importlib.import_module("news_pipeline.db")
MODELS = importlib.import_module("news_pipeline.models")
ARCHIVER = load_module(ROOT / "scripts" / "archive_news_urls.py", "news_pipeline_archive_news_urls")


class _FakeResponse:
    def __init__(self, body: bytes, final_url: str = "https://example.com/final"):
        self.status = 200
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self._body = body
        self._final_url = final_url

    def read(self, n: int = -1) -> bytes:
        if n < 0:
            return self._body
        return self._body[:n]

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ArchiveNewsUrlsTests(unittest.TestCase):
    def _seed_article(self, db_path: Path, url: str = "https://example.com/a") -> str:
        store = DB.NewsArticleStore(db_path)
        try:
            candidate = MODELS.ArticleCandidate(
                provider="gdelt",
                provider_item_id="seed-1",
                canonical_url=url,
                title="Seed title",
                description="Seed description",
                body="Seed body",
                source_name="example",
                language="en",
                published_at_utc="2026-02-24T09:00:00Z",
                fetched_at_utc="2026-02-25T09:00:00Z",
                provider_published_at_raw="2026-02-24T09:00:00Z",
                raw_payload={"id": "seed-1"},
            )
            up = store.upsert_article(candidate, lane="high_precision")
            return up.article_id
        finally:
            store.close()

    def test_archiver_success_writes_snapshot_and_updates_article(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            archive_root = tmp / "archives"
            article_id = self._seed_article(db_path)

            old_urlopen = ARCHIVER.urllib.request.urlopen
            try:
                ARCHIVER.urllib.request.urlopen = lambda req, timeout=0: _FakeResponse(  # type: ignore[assignment]
                    b"<html><body>hello</body></html>"
                )
                rc = ARCHIVER.main(
                    [
                        "--news-articles-db",
                        str(db_path),
                        "--archive-root",
                        str(archive_root),
                        "--since-hours",
                        "0",
                        "--mode",
                        "best_effort",
                    ]
                )
            finally:
                ARCHIVER.urllib.request.urlopen = old_urlopen  # type: ignore[assignment]

            self.assertEqual(rc, 0)

            conn = sqlite3.connect(str(db_path))
            try:
                row = conn.execute(
                    "SELECT archive_url, archive_text_path, archive_provider FROM articles WHERE article_id = ?",
                    (article_id,),
                ).fetchone()
                self.assertIsNotNone(row)
                assert row is not None
                archive_url = str(row[0] or "")
                archive_text_path = str(row[1] or "")
                self.assertTrue(archive_url)
                self.assertTrue(archive_text_path)
                self.assertEqual(str(row[2] or ""), "local_snapshot")
                snapshot_path = Path(archive_url)
                text_path = Path(archive_text_path)
                self.assertTrue(snapshot_path.exists())
                self.assertTrue(text_path.exists())
                with gzip.open(snapshot_path, "rb") as fh:
                    payload = fh.read().decode("utf-8")
                self.assertIn("hello", payload)
                with gzip.open(text_path, "rb") as fh:
                    text_payload = fh.read().decode("utf-8")
                self.assertIn("hello", text_payload)
                archive_row = conn.execute(
                    "SELECT status, capture_mode, text_chars FROM article_archives WHERE article_id = ?",
                    (article_id,),
                ).fetchone()
                self.assertIsNotNone(archive_row)
                assert archive_row is not None
                self.assertEqual(str(archive_row[0] or ""), "success")
                self.assertEqual(str(archive_row[1] or ""), "raw")
                self.assertGreater(int(archive_row[2] or 0), 0)
            finally:
                conn.close()

    def test_archiver_required_mode_fails_on_fetch_error(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            self._seed_article(db_path, url="https://example.com/fail")

            old_urlopen = ARCHIVER.urllib.request.urlopen
            try:
                def _raise(*args, **kwargs):
                    raise urllib.error.URLError("boom")
                ARCHIVER.urllib.request.urlopen = _raise  # type: ignore[assignment]
                rc = ARCHIVER.main(
                    [
                        "--news-articles-db",
                        str(db_path),
                        "--archive-root",
                        str(tmp / "archives"),
                        "--since-hours",
                        "0",
                        "--mode",
                        "required",
                    ]
                )
            finally:
                ARCHIVER.urllib.request.urlopen = old_urlopen  # type: ignore[assignment]

            self.assertEqual(rc, 1)

            conn = sqlite3.connect(str(db_path))
            try:
                row = conn.execute(
                    "SELECT status, attempts FROM article_archives LIMIT 1"
                ).fetchone()
                self.assertIsNotNone(row)
                assert row is not None
                self.assertEqual(str(row[0] or ""), "failed")
                self.assertEqual(int(row[1] or 0), 1)
            finally:
                conn.close()

    def test_extract_clean_text_removes_tags_and_scripts(self):
        raw = b"""
        <html><head><script>console.log('x')</script></head>
        <body><article><h1>Title</h1><p>Alpha <b>beta</b>.</p></article></body></html>
        """
        text = ARCHIVER._extract_clean_text(raw)
        self.assertIn("Title", text)
        self.assertIn("Alpha beta.", text)
        self.assertNotIn("console.log", text)

    def test_cookie_file_applies_cookie_header(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "news_articles.sqlite"
            archive_root = tmp / "archives"
            cookie_file = tmp / "cookie.txt"
            cookie_file.write_text("Cookie: sessionid=abc123; paywall=1", encoding="utf-8")
            self._seed_article(db_path, url="https://example.com/cookie")

            seen_cookie = {"value": ""}
            old_urlopen = ARCHIVER.urllib.request.urlopen
            try:
                def _fake(req, timeout=0):
                    seen_cookie["value"] = str(req.headers.get("Cookie") or req.headers.get("cookie") or "")
                    return _FakeResponse(b"<html><body>cookie ok</body></html>")

                ARCHIVER.urllib.request.urlopen = _fake  # type: ignore[assignment]
                rc = ARCHIVER.main(
                    [
                        "--news-articles-db",
                        str(db_path),
                        "--archive-root",
                        str(archive_root),
                        "--since-hours",
                        "0",
                        "--mode",
                        "required",
                        "--fetch-mode",
                        "raw",
                        "--cookie-file",
                        str(cookie_file),
                    ]
                )
            finally:
                ARCHIVER.urllib.request.urlopen = old_urlopen  # type: ignore[assignment]

            self.assertEqual(rc, 0)
            self.assertIn("sessionid=abc123", seen_cookie["value"])

    def test_render_python_symlink_path_is_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            py_link = tmp / "py-link"
            py_link.symlink_to(Path(sys.executable))

            seen = {"cmd": []}
            old_run = ARCHIVER.subprocess.run
            try:
                def _fake_run(cmd, stdout=None, stderr=None, text=None, timeout=None):
                    seen["cmd"] = list(cmd)
                    out_html = Path(cmd[cmd.index("--_render-out-html") + 1])
                    out_meta = Path(cmd[cmd.index("--_render-out-meta") + 1])
                    out_html.write_bytes(b"<html><body>rendered</body></html>")
                    out_meta.write_text('{"final_url":"https://example.com/final"}', encoding="utf-8")

                    class _Result:
                        returncode = 0
                        stdout = ""
                        stderr = ""

                    return _Result()

                ARCHIVER.subprocess.run = _fake_run  # type: ignore[assignment]
                body, final_url = ARCHIVER._fetch_url_html_rendered(
                    url="https://example.com/a",
                    timeout_sec=10,
                    max_bytes=100_000,
                    user_agent="ua",
                    cookie_header="",
                    render_python=str(py_link),
                )
            finally:
                ARCHIVER.subprocess.run = old_run  # type: ignore[assignment]

            self.assertEqual(seen["cmd"][0], str(py_link))
            self.assertIn(b"rendered", body)
            self.assertEqual(final_url, "https://example.com/final")

    def test_render_helper_timeout_is_reported(self):
        old_run = ARCHIVER.subprocess.run
        try:
            def _timeout(*args, **kwargs):
                raise ARCHIVER.subprocess.TimeoutExpired(cmd="render", timeout=5)

            ARCHIVER.subprocess.run = _timeout  # type: ignore[assignment]
            with self.assertRaises(RuntimeError) as ctx:
                ARCHIVER._fetch_url_html_rendered(
                    url="https://example.com/a",
                    timeout_sec=3,
                    max_bytes=100_000,
                    user_agent="ua",
                    cookie_header="",
                    render_python=str(Path(sys.executable)),
                )
            self.assertIn("render_helper_timeout", str(ctx.exception))
        finally:
            ARCHIVER.subprocess.run = old_run  # type: ignore[assignment]


if __name__ == "__main__":
    unittest.main()
