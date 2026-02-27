import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODULE_PATH = Path(__file__).resolve().parent / "collect_au_finance_news.py"
COLLECTOR = load_module(MODULE_PATH, "collect_au_finance_news")


class TestCollectorHelpers(unittest.TestCase):
    def test_parse_sources_dedupes_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sources.txt"
            path.write_text(
                "# note\nauto:https://www.afr.com\n\nhttps://www.afr.com\nrss:https://www.abc.net.au/news/feed/51120/rss.xml\n",
                encoding="utf-8",
            )
            parsed = COLLECTOR.parse_sources(path)
            self.assertEqual(len(parsed), 2)
            self.assertEqual(parsed[0].mode, "auto")
            self.assertEqual(parsed[0].url, "https://www.afr.com/")
            self.assertEqual(parsed[1].mode, "rss")
            self.assertEqual(parsed[1].url, "https://www.abc.net.au/news/feed/51120/rss.xml")

    def test_canonicalize_url_drops_tracking_params(self):
        canonical = COLLECTOR.canonicalize_url(
            "https://www.example.com/news/story/?utm_source=rss&ref=abc&id=123"
        )
        self.assertEqual(canonical, "https://example.com/news/story?id=123")

    def test_parse_domain_list(self):
        domains = COLLECTOR.parse_domain_list("capitalbrief.com, https://www.afr.com/markets, www.theguardian.com")
        self.assertEqual(domains, ["capitalbrief.com", "afr.com", "theguardian.com"])

    def test_parse_feed_entries_from_xml(self):
        xml_payload = """
        <rss version="2.0">
          <channel>
            <item>
              <title>ASX update</title>
              <link>https://www.afr.com/markets/asx-update?utm_source=rss</link>
              <pubDate>Thu, 26 Feb 2026 05:00:00 GMT</pubDate>
            </item>
          </channel>
        </rss>
        """
        entries = COLLECTOR.parse_feed_entries_from_xml(xml_payload)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, "https://afr.com/markets/asx-update")
        self.assertEqual(entries[0].title, "ASX update")
        self.assertIsNotNone(entries[0].published_at)

    def test_extract_candidate_urls_from_html(self):
        html = """
        <html><body>
          <a href="/markets/equities/article-abc">A</a>
          <a href="/sport/cricket/article-def">B</a>
          <a href="/feed.xml">Feed</a>
        </body></html>
        """
        candidates, feeds = COLLECTOR.extract_candidate_urls_from_html(
            base_url="https://www.afr.com/markets",
            html_text=html,
            max_candidates=20,
        )
        self.assertIn("https://afr.com/markets/equities/article-abc", candidates)
        self.assertIn("https://afr.com/feed.xml", feeds)

    def test_extract_candidate_urls_prioritizes_article_like_paths(self):
        html = """
        <html><body>
          <a href="/business/markets">Markets</a>
          <a href="/wealth/personal-finance">Personal finance</a>
          <a href="/business/markets/asx-200-live-coles-interim-profit/live-coverage/37aaf6a9469c439db5198faed9f268be">Live article</a>
        </body></html>
        """
        candidates, _feeds = COLLECTOR.extract_candidate_urls_from_html(
            base_url="https://www.theaustralian.com.au/business",
            html_text=html,
            max_candidates=1,
        )
        self.assertEqual(
            candidates[0],
            "https://theaustralian.com.au/business/markets/asx-200-live-coles-interim-profit/live-coverage/37aaf6a9469c439db5198faed9f268be",
        )

    def test_extract_afr_article_urls_from_html(self):
        html = r"""
        <script>
          {"url":"https:\/\/www.afr.com\/companies\/energy\/energyaustralia-plans-retail-revamp-after-competition-dents-profit-20260226-p5o5n9"}
        </script>
        """
        urls = COLLECTOR.extract_afr_article_urls_from_html(
            base_url="https://www.afr.com/companies",
            html_text=html,
            max_candidates=20,
        )
        self.assertIn(
            "https://afr.com/companies/energy/energyaustralia-plans-retail-revamp-after-competition-dents-profit-20260226-p5o5n9",
            urls,
        )

    def test_extract_article_body_from_jsonld(self):
        html = r"""
        <script type="application/ld+json">
          {"@type":"NewsArticle","articleBody":"Line one.\nLine two with more detail."}
        </script>
        """
        body = COLLECTOR.extract_article_body_from_jsonld(html)
        self.assertIn("Line one.", body)
        self.assertIn("Line two with more detail.", body)

    def test_extract_meta_description_from_html(self):
        html = """
        <html><head>
          <meta property="og:description" content="Company profit jumped after strong ASX session." />
        </head></html>
        """
        body = COLLECTOR.extract_meta_description_from_html(html)
        self.assertIn("Company profit jumped", body)

    def test_extract_description_from_jsonld(self):
        html = r"""
        <script type="application/ld+json">
          {"@type":"NewsArticle","description":"Budget pressures and inflation risks remain elevated."}
        </script>
        """
        body = COLLECTOR.extract_description_from_jsonld(html)
        self.assertIn("Budget pressures", body)

    def test_choose_best_article_body_prefers_longer_source(self):
        class DummyNewspaper:
            @staticmethod
            def fulltext(_html: str) -> str:
                return "short fulltext"

        html = r"""
        <script type="application/ld+json">
          {"@type":"NewsArticle","articleBody":"This is a much longer JSON-LD article body that should be selected."}
        </script>
        """
        body, source, lengths = COLLECTOR.choose_best_article_body(
            newspaper_module=DummyNewspaper(),
            title="ASX Update",
            meta_description="",
            item_text="short body",
            item_html=html,
        )
        self.assertEqual(source, "jsonld_articleBody")
        self.assertIn("much longer JSON-LD article body", body)
        self.assertGreater(lengths.get("jsonld_articleBody", 0), lengths.get("newspaper_text", 0))

    def test_choose_best_article_body_uses_meta_description_when_text_missing(self):
        class DummyNewspaper:
            @staticmethod
            def fulltext(_html: str) -> str:
                return ""

        body, source, lengths = COLLECTOR.choose_best_article_body(
            newspaper_module=DummyNewspaper(),
            title="RBA update",
            meta_description="Interest rate outlook remains uncertain amid inflation concerns.",
            item_text="",
            item_html="",
        )
        self.assertEqual(source, "meta_description")
        self.assertIn("RBA update", body)
        self.assertGreater(lengths.get("meta_description", 0), 20)

    def test_fallback_feed_urls_for_afr(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.afr.com/markets")
        self.assertTrue(feeds)
        self.assertIn("https://www.afr.com/rss", feeds)

    def test_fallback_feed_urls_for_capitalbrief(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.capitalbrief.com")
        self.assertTrue(feeds)
        self.assertIn("https://www.capitalbrief.com/rss", feeds)

    def test_fallback_feed_urls_for_kalkine(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.kalkinemedia.com")
        self.assertTrue(feeds)
        self.assertIn("https://www.kalkinemedia.com/rss", feeds)

    def test_fallback_feed_urls_for_benzinga(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.benzinga.com")
        self.assertTrue(feeds)
        self.assertIn("https://www.benzinga.com/feed", feeds)

    def test_fallback_feed_urls_for_the_australian(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.theaustralian.com.au/business")
        self.assertTrue(feeds)
        self.assertIn("https://www.theaustralian.com.au/rss", feeds)

    def test_fallback_feed_urls_for_marketindex(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.marketindex.com.au/news")
        self.assertTrue(feeds)
        self.assertIn("https://www.marketindex.com.au/news/rss", feeds)

    def test_fallback_feed_urls_for_skynews(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.skynews.com.au/business")
        self.assertTrue(feeds)
        self.assertIn("https://www.skynews.com.au/business/feed", feeds)

    def test_fallback_feed_urls_for_stockhead(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://stockhead.com.au")
        self.assertTrue(feeds)
        self.assertIn("https://stockhead.com.au/feed", feeds)

    def test_fallback_feed_urls_for_livewire(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://www.livewiremarkets.com")
        self.assertTrue(feeds)
        self.assertIn("https://www.livewiremarkets.com/feed", feeds)

    def test_fallback_feed_urls_for_yahoo_finance(self):
        feeds = COLLECTOR._fallback_feed_urls_for_source("https://finance.yahoo.com")
        self.assertTrue(feeds)
        self.assertIn("https://finance.yahoo.com/news/rssindex", feeds)

    def test_domain_allowed_accepts_subdomain(self):
        self.assertTrue(COLLECTOR.domain_allowed("markets.afr.com", ["afr.com"]))
        self.assertFalse(COLLECTOR.domain_allowed("example.org", ["afr.com"]))

    def test_finance_url_allowed(self):
        include_tokens = ["/business", "/markets", "/finance"]
        exclude_tokens = ["/sport", "/lifestyle"]
        self.assertTrue(
            COLLECTOR.finance_url_allowed(
                "https://www.afr.com/markets/equity-markets/article-1",
                include_tokens=include_tokens,
                exclude_tokens=exclude_tokens,
            )
        )
        self.assertFalse(
            COLLECTOR.finance_url_allowed(
                "https://www.abc.net.au/news/sport/2026-02-26/test",
                include_tokens=include_tokens,
                exclude_tokens=exclude_tokens,
            )
        )

    def test_looks_like_article_url(self):
        self.assertTrue(
            COLLECTOR.looks_like_article_url(
                "https://www.afr.com/companies/energy/energyaustralia-plans-retail-revamp-after-competition-dents-profit-20260226-p5o5n9"
            )
        )
        self.assertFalse(COLLECTOR.looks_like_article_url("https://www.afr.com/companies/mining"))
        self.assertTrue(
            COLLECTOR.looks_like_article_url(
                "https://www.abc.net.au/news/2026-02-26/grape-growers-welcome-national-vineyard-register-amid-oversupply/106390054"
            )
        )
        self.assertFalse(COLLECTOR.looks_like_article_url("https://www.theguardian.com/australia-news"))

    def test_is_explicitly_non_article_path(self):
        self.assertTrue(COLLECTOR.is_explicitly_non_article_path("https://capitalbrief.com/author/jack-derwin"))
        self.assertTrue(COLLECTOR.is_explicitly_non_article_path("https://capitalbrief.com/topic/earnings"))
        self.assertFalse(
            COLLECTOR.is_explicitly_non_article_path(
                "https://capitalbrief.com/briefing/block-to-cut-workforce-by-more-than-4000-posts-55-full-year-net-income-slide-bddb8250-5656-411c-b33d-43613826d08f"
            )
        )

    def test_is_domain_specific_non_article_path(self):
        self.assertTrue(COLLECTOR.is_domain_specific_non_article_path("https://www.theaustralian.com.au/business/markets"))
        self.assertFalse(
            COLLECTOR.is_domain_specific_non_article_path(
                "https://www.theaustralian.com.au/business/markets/asx-200-live-coles-interim-profit/live-coverage/37aaf6a9469c439db5198faed9f268be"
            )
        )
        self.assertFalse(COLLECTOR.is_domain_specific_non_article_path("https://capitalbrief.com/briefing/some-slug-123"))

    def test_keyword_hits(self):
        hits = COLLECTOR.keyword_hits("ASX earnings guidance raised this quarter", ["asx", "guidance", "crypto"])
        self.assertEqual(hits, ["asx", "guidance"])

    def test_build_record_shape(self):
        article = COLLECTOR.ExtractedArticle(
            source_url="https://www.afr.com",
            source_name="AFR",
            article_url="https://www.afr.com/markets/story-1",
            title="ASX profit update",
            body="A company on the ASX reported a profit increase and improved cash flow.",
            language="en",
            authors=["Author One"],
            published_at=COLLECTOR.coerce_datetime("2026-02-25T09:00:00Z"),
            keyword_hits=["asx", "profit"],
            body_source="jsonld_articleBody",
            body_lengths={"newspaper_text": 120, "jsonld_articleBody": 300},
            raw_html_path="/tmp/raw/article.html",
        )
        rec = COLLECTOR.build_record(article, fetched_at_utc="2026-02-26T00:00:00Z")
        self.assertEqual(rec["title"], "ASX profit update")
        self.assertIn("ASX profit update", rec["text"])
        extra = rec["extra_fields"]
        self.assertEqual(extra["source"], "AFR")
        self.assertEqual(extra["url"], "https://afr.com/markets/story-1")
        self.assertEqual(extra["matched_keywords"], ["asx", "profit"])
        self.assertEqual(extra["body_source"], "jsonld_articleBody")
        self.assertEqual(extra["body_lengths"]["jsonld_articleBody"], 300)
        self.assertEqual(extra["raw_html_path"], "/tmp/raw/article.html")
        self.assertEqual(len(rec["id"]), 40)


if __name__ == "__main__":
    unittest.main()
