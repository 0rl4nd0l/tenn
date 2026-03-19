"""Unit tests for canonical article schema (normalize + validate)."""
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
REPO_ROOT = SCRIPTS.parent
for p in (str(SCRIPTS), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from news_pipeline.canonical_article_schema import (
    normalize_to_canonical,
    validate_canonical_article,
    validate_canonical_article_strict,
)


class TestNormalizeToCanonical(unittest.TestCase):
    def test_maps_id_aliases_to_document_id(self):
        for key in ("id", "record_id", "document_id", "guid"):
            out = normalize_to_canonical({key: "abc123", "date": "2026-01-01", "title": "T"})
            self.assertEqual(out["document_id"], "abc123")

    def test_maps_date_aliases_to_published_at(self):
        out = normalize_to_canonical({"id": "x", "date": "2026-01-15", "title": "T"})
        self.assertEqual(out["published_at"], "2026-01-15")
        out = normalize_to_canonical({"id": "x", "published_at": "2026-02-01T00:00:00Z", "title": "T"})
        self.assertEqual(out["published_at"], "2026-02-01T00:00:00Z")

    def test_maps_body_aliases_to_body(self):
        out = normalize_to_canonical({"id": "x", "date": "2026-01-01", "text": "Body here"})
        self.assertEqual(out["body"], "Body here")
        out = normalize_to_canonical({"id": "x", "date": "2026-01-01", "content": "Content"})
        self.assertEqual(out["body"], "Content")

    def test_extra_fields_used_for_source(self):
        out = normalize_to_canonical({
            "id": "x", "date": "2026-01-01", "title": "T",
            "extra_fields": {"source": "Reuters"},
        })
        self.assertEqual(out["source"], "Reuters")

    def test_falls_back_to_derived_document_id_when_no_id(self):
        out = normalize_to_canonical({"url": "https://example.com/article", "date": "2026-01-01", "title": "T"})
        self.assertTrue(len(out["document_id"]) > 0)
        self.assertEqual(out["title"], "T")


class TestValidateCanonicalArticle(unittest.TestCase):
    def test_valid_minimal_row_passes(self):
        ok, errs = validate_canonical_article({"id": "a1", "date": "2026-01-01", "title": "Headline"})
        self.assertTrue(ok, errs)
        self.assertEqual(errs, [])

    def test_valid_with_body_only_passes(self):
        ok, errs = validate_canonical_article({"id": "a1", "date": "2026-01-01", "body": "Content only"})
        self.assertTrue(ok, errs)

    def test_missing_published_at_fails(self):
        ok, errs = validate_canonical_article({"id": "a1", "title": "T"})
        self.assertFalse(ok)
        self.assertTrue(any("published_at" in e for e in errs))

    def test_missing_document_id_fails(self):
        # No id/url/title so document_id cannot be derived; body-only row still needs an identifier
        ok, errs = validate_canonical_article({"date": "2026-01-01", "body": "Content only"})
        self.assertFalse(ok)
        self.assertTrue(any("document_id" in e or "id" in e for e in errs))

    def test_missing_content_fails(self):
        ok, errs = validate_canonical_article({"id": "a1", "date": "2026-01-01"})
        self.assertFalse(ok)
        self.assertTrue(any("content" in e or "title" in e or "body" in e for e in errs))

    def test_strict_requires_both_title_and_body(self):
        ok, errs = validate_canonical_article(
            {"id": "a1", "date": "2026-01-01", "title": "T"},
            strict=True,
        )
        self.assertFalse(ok)
        self.assertTrue(any("strict" in e or "body" in e for e in errs))
        ok, errs = validate_canonical_article(
            {"id": "a1", "date": "2026-01-01", "title": "T", "body": "B"},
            strict=True,
        )
        self.assertTrue(ok, errs)


class TestValidateCanonicalArticleStrict(unittest.TestCase):
    def test_strict_helper_requires_both(self):
        ok, _ = validate_canonical_article_strict({"id": "a1", "date": "2026-01-01", "title": "T", "body": "B"})
        self.assertTrue(ok)
        ok, _ = validate_canonical_article_strict({"id": "a1", "date": "2026-01-01", "title": "T"})
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
