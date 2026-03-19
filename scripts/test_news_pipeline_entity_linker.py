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


class EntityLinkerTests(unittest.TestCase):
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
            tickers.write_text("GOOD\n", encoding="utf-8")
            identity_map.write_text(
                json.dumps({"GOOD": {"canonical_names": ["Good ASX Issuer"], "aliases": ["GOOD"]}}),
                encoding="utf-8",
            )
            linker = LINKER_MOD.EntityLinker(ticker_universe_path=tickers, identity_map_path=identity_map)
            lower_links = linker.link_article(
                article_id="art_4",
                title="Company says the outlook is good",
                description="",
                body="Management said results were good and margins improved.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            upper_links = linker.link_article(
                article_id="art_5",
                title="GOOD responds to takeover approach",
                description="",
                body="Shares in GOOD moved after the statement.",
                published_at_utc="2026-02-24T00:00:00Z",
            )
            self.assertFalse(lower_links)
            self.assertTrue(any(lnk.ticker == "GOOD" and lnk.method == "ticker_token" for lnk in upper_links))


if __name__ == "__main__":
    unittest.main()
