import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
LINKER_MOD = importlib.import_module("news_pipeline.entity_linker")
CLI_COMMON = importlib.import_module("news_pipeline.cli_common")

A2M_RECALL_TITLE = "A2 Milk shares plunge after finding toxins in infant formula"
A2M_RECALL_BODY = (
    "The a2 Milk Company said it was working through a recall of infant formula "
    "after testing found toxins. ASX:A2M investors reacted to the update."
)
DEFAULT_LINKER_TICKERS = ("CBA", "WBC", "NAB", "INA", "WES", "A2M")
EXPLICIT_SYMBOL_CASES = (
    ("ASX:CBA", "CBA"),
    ("ASX:WBC", "WBC"),
    ("ASX:NAB", "NAB"),
    ("ASX:INA", "INA"),
    ("ASX:WES", "WES"),
    ("ASX:GOLD", "GOLD"),
    ("CBA.AX", "CBA"),
    ("NAB.AX", "NAB"),
)
ALIAS_CASES = (
    ("Commonwealth Bank of Australia", "CBA"),
    ("Westpac Banking", "WBC"),
    ("National Australia Bank", "NAB"),
    ("Wesfarmers", "WES"),
    ("Ingenia Communities", "INA"),
)


class EntityLinkerTests(unittest.TestCase):
    def _default_linker(self):
        return LINKER_MOD.EntityLinker(
            ticker_universe_path=CLI_COMMON.DEFAULT_TICKER_UNIVERSE,
            identity_map_path=CLI_COMMON.DEFAULT_IDENTITY_MAP,
        )

    def test_high_precision_explicit_symbol(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            identity_map = tmp / "identity.json"
            tickers.write_text("BHP\nCSL\nXYZ\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "BHP": {"canonical_names": ["BHP Group"], "aliases": []},
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL"]},
                        "XYZ": {"canonical_names": ["Example Holdings"], "aliases": ["CSL"]},
                    }
                ),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)
            links = linker.link_article(
                article_id="art_1",
                title="ASX:BHP jumps after earnings beat",
                description="",
                body="BHP.AX rose on stronger guidance.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            hp = [lnk for lnk in links if lnk.lane == "high_precision" and lnk.ticker == "BHP"]
            self.assertTrue(hp)
            self.assertTrue(all((lnk.matched_span_start or 0) >= 0 for lnk in hp))
            self.assertTrue(any(lnk.method == "explicit_symbol" for lnk in hp))

    def test_ambiguous_alias_filtered_from_precision(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            identity_map = tmp / "identity.json"
            tickers.write_text("CSL\nXYZ\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL"]},
                        "XYZ": {"canonical_names": ["Example Holdings"], "aliases": ["CSL"]},
                    }
                ),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)
            links = linker.link_article(
                article_id="art_2",
                title="CSL posts trading update",
                description="",
                body="CSL said guidance remains unchanged.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            hp = [lnk for lnk in links if lnk.lane == "high_precision"]
            hr = [lnk for lnk in links if lnk.lane == "high_recall"]
            # Ambiguous acronym alias should not produce precision links.
            self.assertFalse(hp)
            # Recall should still keep potential signals.
            self.assertTrue(any(lnk.ticker == "CSL" for lnk in hr))

    def test_generic_single_word_aliases_are_not_linked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            identity_map = tmp / "identity.json"
            tickers.write_text("BNZ\nCC5\nCXO\nDME\nGTK\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "BNZ": {"canonical_names": ["Banzai Energy"], "aliases": ["following"]},
                        "CC5": {"canonical_names": ["Clever Culture Systems"], "aliases": ["Systems"]},
                        "CXO": {"canonical_names": ["Core Lithium"], "aliases": ["Markets"]},
                        "DME": {"canonical_names": ["Demo Mining"], "aliases": ["Investment"]},
                        "GTK": {"canonical_names": ["Gentrack"], "aliases": ["Investment"]},
                    }
                ),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)
            links = linker.link_article(
                article_id="art_3",
                title="Markets are cautious following the investment update from systems vendors",
                description="",
                body="The following session covered broad markets and investment themes.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            self.assertFalse(links)

    def test_case_sensitive_ticker_token_avoids_common_word_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            identity_map = tmp / "identity.json"
            tickers.write_text("NICE\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps({"NICE": {"canonical_names": ["Nice ASX Issuer"], "aliases": ["NICE"]}}),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)
            lower_links = linker.link_article(
                article_id="art_4",
                title="Company says the outlook is nice",
                description="",
                body="Management said results were nice and margins improved.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            upper_links = linker.link_article(
                article_id="art_5",
                title="NICE responds to takeover approach",
                description="",
                body="Shares in NICE moved after the statement.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            self.assertFalse(lower_links)
            self.assertTrue(any(lnk.ticker == "NICE" and lnk.method == "ticker_token" for lnk in upper_links))

    def test_default_identity_map_links_a2m_recall_article(self):
        with tempfile.TemporaryDirectory() as td:
            tickers = Path(td) / "tickers.txt"
            tickers.write_text("BHP\n", encoding="utf-8")
            linker = LINKER_MOD.EntityLinker(
                ticker_universe_path=tickers,
                identity_map_path=CLI_COMMON.DEFAULT_IDENTITY_MAP,
            )

            links = linker.link_article(
                article_id="art_a2m_recall",
                title=A2M_RECALL_TITLE,
                description="",
                body=A2M_RECALL_BODY,
                published_at_utc="2026-05-05T00:00:00Z",
            )

        a2m_links = [lnk for lnk in links if lnk.ticker == "A2M"]
        self.assertTrue(a2m_links)
        self.assertTrue(any(lnk.lane == "high_precision" for lnk in a2m_links))

    def test_default_identity_map_links_a2m_alias_forms(self):
        with tempfile.TemporaryDirectory() as td:
            tickers = Path(td) / "tickers.txt"
            tickers.write_text("BHP\n", encoding="utf-8")
            linker = LINKER_MOD.EntityLinker(
                ticker_universe_path=tickers,
                identity_map_path=CLI_COMMON.DEFAULT_IDENTITY_MAP,
            )

            forms = [
                "A2 Milk",
                "a2 Milk",
                "The a2 Milk Company",
                "ASX:A2M",
                "ASX: A2M",
                "A2M.AX",
            ]
            for form in forms:
                with self.subTest(form=form):
                    links = linker.link_article(
                        article_id="art_a2m_forms",
                        title=f"{form} recall update",
                        description="",
                        body="The infant formula recall remains under review.",
                        published_at_utc="2026-05-05T00:00:00Z",
                    )
                    self.assertTrue(any(lnk.ticker == "A2M" for lnk in links))

    def test_identity_map_can_opt_in_ticker_missing_from_universe(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tickers = tmp / "tickers.txt"
            identity_map = tmp / "identity.json"
            tickers.write_text("BHP\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps(
                    {
                        "BHP": {"canonical_names": ["BHP Group"], "aliases": []},
                        "A2M": {
                            "canonical_names": ["The a2 Milk Company"],
                            "aliases": ["A2 Milk"],
                            "news_entity_linking_enabled": True,
                        },
                        "ZZZ": {
                            "canonical_names": ["ZZZ Example"],
                            "aliases": ["ZZZ Example"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)

            links = linker.link_article(
                article_id="art_a2m_universe_gap",
                title="A2 Milk recall update",
                description="",
                body="ASX:ZZZ is not in the ticker universe and has no opt-in flag.",
                published_at_utc="2026-05-05T00:00:00Z",
            )

            self.assertTrue(any(lnk.ticker == "A2M" for lnk in links))
            self.assertFalse(any(lnk.ticker == "ZZZ" for lnk in links))

    def test_default_effective_tickers_cover_major_news_linking_gaps(self):
        linker = self._default_linker()

        for ticker in DEFAULT_LINKER_TICKERS:
            with self.subTest(ticker=ticker):
                self.assertIn(ticker, linker.tickers)

    def test_default_linker_links_explicit_symbols_and_relevance_rows(self):
        relevance_mod = importlib.import_module("news_pipeline.relevance")
        linker = self._default_linker()

        for form, ticker in EXPLICIT_SYMBOL_CASES:
            with self.subTest(form=form, ticker=ticker):
                title = f"{form} shares move after a trading update"
                links = linker.link_article(
                    article_id=f"art_explicit_{ticker}",
                    title=title,
                    description="",
                    body="The company update was published before market open.",
                    published_at_utc="2026-05-05T00:00:00Z",
                )
                self.assertTrue(
                    any(lnk.ticker == ticker and lnk.method == "explicit_symbol" for lnk in links),
                    f"missing explicit link for {form}",
                )

                rows = relevance_mod.score_article_relevance(
                    article_id=f"art_explicit_{ticker}",
                    title=title,
                    description="",
                    body="The company update was published before market open.",
                    links=links,
                )
                self.assertTrue(any(row.ticker == ticker for row in rows), f"missing relevance row for {form}")

    def test_default_linker_links_configured_strong_aliases(self):
        linker = self._default_linker()

        for alias, ticker in ALIAS_CASES:
            with self.subTest(alias=alias, ticker=ticker):
                links = linker.link_article(
                    article_id=f"art_alias_{ticker}",
                    title=f"{alias} posts a trading update",
                    description="",
                    body="Management said the update reflected current trading conditions.",
                    published_at_utc="2026-05-05T00:00:00Z",
                )
                self.assertTrue(
                    any(lnk.ticker == ticker and lnk.method == "alias_strict" for lnk in links),
                    f"missing alias link for {alias}",
                )

    def test_stopword_like_tickers_do_not_plain_match_but_explicit_symbols_link(self):
        linker = self._default_linker()

        unsafe_links = linker.link_article(
            article_id="art_stopword_plain",
            title="Gold and core education providers report good demand",
            description="CORE GOLD GOOD EDU are used here as plain tokens, not listed symbols.",
            body="The article discussed gold prices, core strategy, good demand and education trends.",
            published_at_utc="2026-05-05T00:00:00Z",
        )
        for ticker in ("GOLD", "CORE", "GOOD", "EDU"):
            with self.subTest(ticker=ticker, mode="plain"):
                self.assertFalse(any(lnk.ticker == ticker for lnk in unsafe_links))

        for form, ticker in (("ASX:GOLD", "GOLD"), ("GOLD.AX", "GOLD"), ("ASX:CORE", "CORE"), ("CORE.AX", "CORE")):
            with self.subTest(form=form, ticker=ticker, mode="explicit"):
                links = linker.link_article(
                    article_id=f"art_stopword_explicit_{ticker}",
                    title=f"{form} releases a market update",
                    description="",
                    body="The listed entity update referenced the explicit ASX symbol.",
                    published_at_utc="2026-05-05T00:00:00Z",
                )
                self.assertTrue(
                    any(lnk.ticker == ticker and lnk.method == "explicit_symbol" for lnk in links),
                    f"missing explicit stopword-like ticker link for {form}",
                )


if __name__ == "__main__":
    unittest.main()
