#!/usr/bin/env python3
import importlib.util
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
MOD = load_module(SCRIPTS / "build_asx_identity_map_from_filings.py", "build_asx_identity_map_from_filings")


def init_test_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE documents (
              document_id TEXT PRIMARY KEY,
              ticker TEXT,
              title TEXT,
              pdf_path TEXT,
              published_at TEXT,
              ingested_at TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE extraction_runs (
              run_id TEXT PRIMARY KEY,
              document_id TEXT,
              status TEXT,
              structured_json TEXT,
              created_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


class BuildAsxIdentityMapFromFilingsTests(unittest.TestCase):
    def test_build_identity_map_extracts_canonical_and_aliases_with_merge(self):
        fixture_text = (SCRIPTS / "testdata" / "asx_identity_first_page_fixture.txt").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "fe_local.db"
            docs_root = tmp / "docs"
            tickers = tmp / "tickers.txt"
            out_json = tmp / "ticker_identity_map.json"
            cba_pdf = docs_root / "CBA" / "other" / "2026-02-22_cba-presentation_test.pdf"
            cba_pdf.parent.mkdir(parents=True, exist_ok=True)
            cba_pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")

            init_test_db(db_path)
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO documents(document_id, ticker, title, pdf_path, published_at, ingested_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("doc_bhp", "BHP", "Half Year Results", str(tmp / "missing_bhp.pdf"), "2026-02-20", "2026-02-20"),
                )
                cur.execute(
                    """
                    INSERT INTO documents(document_id, ticker, title, pdf_path, published_at, ingested_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("doc_cba", "CBA", "Investor Presentation", str(cba_pdf), "2026-02-22", "2026-02-22"),
                )
                cur.execute(
                    """
                    INSERT INTO extraction_runs(run_id, document_id, status, structured_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "run_bhp",
                        "doc_bhp",
                        "success",
                        json.dumps(
                            {
                                "company_profile": {
                                    "legal_name": "BHP Group Limited",
                                    "aliases": ["BHP Group"],
                                }
                            }
                        ),
                        "2026-02-21",
                    ),
                )
                conn.commit()
            finally:
                conn.close()

            tickers.write_text("BHP\nCBA\nCSL\n", encoding="utf-8")
            out_json.write_text(
                json.dumps({"CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]}}, indent=2),
                encoding="utf-8",
            )

            def fake_extract(path: Path, max_chars: int = 24000) -> str:
                if str(path) == str(cba_pdf):
                    return fixture_text
                return ""

            with mock.patch.object(MOD, "extract_first_page_text", side_effect=fake_extract):
                payload, summary = MOD.build_identity_map_from_filings(
                    database_url=f"sqlite:///{db_path}",
                    asx_tickers_file=tickers,
                    docs_root=docs_root,
                    out_json=out_json,
                    merge=True,
                )

            self.assertEqual(summary["tickers_total"], 3)
            self.assertGreaterEqual(summary["tickers_with_canonical_name"], 3)
            self.assertIn("BHP", payload)
            self.assertIn("CBA", payload)
            self.assertIn("CSL", payload)

            bhp_canonical = payload["BHP"]["canonical_names"]
            self.assertTrue(any("BHP Group Limited" == item for item in bhp_canonical))
            self.assertIn("BHP Group", payload["BHP"]["aliases"])
            self.assertNotIn("BHP", payload["BHP"]["aliases"])

            cba_canonical_joined = " | ".join(payload["CBA"]["canonical_names"]).lower()
            self.assertIn("commonwealth bank of australia", cba_canonical_joined)

            self.assertIn("CSL Limited", payload["CSL"]["canonical_names"])
            self.assertIn("CSL Ltd", payload["CSL"]["aliases"])

            MOD.atomic_write_json(out_json, payload)
            first_text = out_json.read_text(encoding="utf-8")
            MOD.atomic_write_json(out_json, payload)
            second_text = out_json.read_text(encoding="utf-8")
            self.assertEqual(first_text, second_text)

    def test_merge_false_replaces_existing_entries(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "fe_local.db"
            docs_root = tmp / "docs"
            tickers = tmp / "tickers.txt"
            out_json = tmp / "ticker_identity_map.json"

            init_test_db(db_path)
            tickers.write_text("CSL\n", encoding="utf-8")
            out_json.write_text(
                json.dumps({"CSL": {"canonical_names": ["CSL Limited"], "aliases": ["CSL Ltd"]}}, indent=2),
                encoding="utf-8",
            )

            payload, summary = MOD.build_identity_map_from_filings(
                database_url=f"sqlite:///{db_path}",
                asx_tickers_file=tickers,
                docs_root=docs_root,
                out_json=out_json,
                merge=False,
            )
            self.assertEqual(summary["tickers_total"], 1)
            self.assertGreaterEqual(summary["tickers_with_canonical_name"], 1)
            self.assertIn("CSL", payload)
            self.assertIn("CSL Limited", payload["CSL"]["canonical_names"])
            self.assertNotIn("CSL Ltd", payload["CSL"]["aliases"])

    def test_filename_based_fallback_and_missing_report(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            db_path = tmp / "fe_local.db"
            docs_root = tmp / "docs"
            tickers = tmp / "tickers.txt"
            out_json = tmp / "ticker_identity_map.json"
            report_path = tmp / "missing.json"

            init_test_db(db_path)
            pdf_path = docs_root / "ABCD" / "other" / "ABCD-Resources-Limited-Annual-Report.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF-1.4\n% synthetic\n")
            tickers.write_text("ABCD\nZZZZ\n", encoding="utf-8")

            with mock.patch.object(MOD, "extract_first_page_text", return_value=""):
                payload, summary = MOD.build_identity_map_from_filings(
                    database_url=f"sqlite:///{db_path}",
                    asx_tickers_file=tickers,
                    docs_root=docs_root,
                    out_json=out_json,
                    merge=False,
                    report_missing_path=report_path,
                )

            self.assertEqual(summary["tickers_total"], 2)
            self.assertEqual(summary["tickers_with_canonical_name"], 2)
            self.assertIn("ABCD", payload)
            self.assertTrue(any("ABCD Resources" in name for name in payload["ABCD"]["canonical_names"]))
            # For truly missing signals, conservative synthetic fallback is still deterministic.
            self.assertIn("ZZZZ ASX Issuer", payload["ZZZZ"]["canonical_names"])

            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["missing_count"], 0)

    def test_sanitize_identity_entry_removes_generic_names_and_aliases(self):
        entry = MOD.sanitize_identity_entry(
            ticker="SGI",
            entry={
                "canonical_names": [
                    "The Group",
                    "Stealth Group Limited",
                    "Australia Limited",
                    "Services Limited",
                ],
                "aliases": [
                    "Group",
                    "The",
                    "Limited",
                    "Australia",
                    "Stealth",
                    "SGI",
                    "ASX",
                    "Issuer",
                ],
            },
        )
        self.assertIn("Stealth Group Limited", entry["canonical_names"])
        self.assertNotIn("The Group", entry["canonical_names"])
        self.assertNotIn("Australia Limited", entry["canonical_names"])
        self.assertNotIn("Services Limited", entry["canonical_names"])
        self.assertIn("Stealth", entry["aliases"])
        self.assertIn("SGI", entry["aliases"])
        self.assertNotIn("Group", entry["aliases"])
        self.assertNotIn("The", entry["aliases"])
        self.assertNotIn("Limited", entry["aliases"])
        self.assertNotIn("Australia", entry["aliases"])
        self.assertNotIn("ASX", entry["aliases"])
        self.assertNotIn("Issuer", entry["aliases"])

    def test_sanitize_identity_entry_drops_noisy_acronym_alias(self):
        entry = MOD.sanitize_identity_entry(
            ticker="GEM",
            entry={
                "canonical_names": [
                    "Authorised for release by G8 Education Limited",
                    "G8 Education Limited",
                ],
                "aliases": [
                    "Authorised for release by G8 Education",
                    "G8 Education",
                    "ARGE",
                ],
            },
        )
        self.assertIn("G8 Education Limited", entry["canonical_names"])
        self.assertNotIn("Authorised for release by G8 Education Limited", entry["canonical_names"])
        self.assertIn("G8 Education", entry["aliases"])
        self.assertNotIn("Authorised for release by G8 Education", entry["aliases"])
        self.assertNotIn("ARGE", entry["aliases"])

    def test_sanitize_identity_entry_strips_leading_connector(self):
        entry = MOD.sanitize_identity_entry(
            ticker="CAE",
            entry={
                "canonical_names": [
                    "in Cannindah Resources Limited",
                    "Cannindah Resources Limited",
                ],
                "aliases": [],
            },
        )
        self.assertIn("Cannindah Resources Limited", entry["canonical_names"])
        self.assertNotIn("in Cannindah Resources Limited", entry["canonical_names"])


if __name__ == "__main__":
    unittest.main()
