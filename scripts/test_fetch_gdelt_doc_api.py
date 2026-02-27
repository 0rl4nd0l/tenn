import importlib.util
import sys
import unittest
from pathlib import Path


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

GDELT = load_module(str(SCRIPTS / "fetch_gdelt_doc_api.py"), "fetch_gdelt_doc_api")


class TestFetchGdeltDocApi(unittest.TestCase):
    def test_parse_gdelt_datetime_compact_utc(self):
        parsed = GDELT.parse_gdelt_datetime("20260224143000")
        self.assertEqual(parsed, "2026-02-24T14:30:00Z")
        self.assertEqual(GDELT.iso_date(parsed), "2026-02-24")

    def test_parse_gdelt_datetime_compact_t_utc(self):
        parsed = GDELT.parse_gdelt_datetime("20260224T143000Z")
        self.assertEqual(parsed, "2026-02-24T14:30:00Z")
        self.assertEqual(GDELT.iso_date(parsed), "2026-02-24")

    def test_build_doc_api_url_rejects_mixed_window_args(self):
        with self.assertRaises(ValueError):
            GDELT.build_doc_api_url(
                query="tesla",
                mode="ArtList",
                max_records=250,
                sort="datedesc",
                timespan="1day",
                start_datetime="20260201000000",
                end_datetime="20260202000000",
                api_url=GDELT.DOC_API_URL,
            )

    def test_normalize_article_row_prefers_fetched_body(self):
        article = {
            "url": "https://example.com/news/123",
            "title": "Tesla raises production guidance",
            "seendate": "20260224143000",
            "domain": "example.com",
            "language": "English",
            "sourcecountry": "US",
        }
        row, reason = GDELT.normalize_article_row(
            article=article,
            query="tesla",
            source_label="GDELT",
            topic="ev",
            full_text="Tesla said production is increasing through 2026 and margins remain resilient." * 6,
            min_body_chars=200,
            include_raw=False,
        )
        self.assertEqual(reason, "ok")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["source"], "example.com")
        self.assertEqual(row["topic"], "ev")
        self.assertEqual(row["date"], "2026-02-24")
        self.assertIn("Tesla raises production guidance", row["text"])

    def test_normalize_article_row_drops_short_without_body(self):
        article = {
            "url": "https://example.com/news/short",
            "title": "Short title only",
            "seendate": "20260224143000",
            "domain": "example.com",
        }
        row, reason = GDELT.normalize_article_row(
            article=article,
            query="tesla",
            source_label="GDELT",
            topic="",
            full_text="",
            min_body_chars=120,
            include_raw=False,
        )
        self.assertIsNone(row)
        self.assertEqual(reason, "short_body")


if __name__ == "__main__":
    unittest.main()
