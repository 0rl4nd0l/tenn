import importlib.util
import sys
import types
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
MOD = load_module(str(ROOT / "scripts" / "build_qualitative_context_db.py"), "build_qualitative_context_db")


class TestQualitativeContextDb(unittest.TestCase):
    def test_extract_target_sections_detects_mda_and_risk(self):
        sample = """
        MANAGEMENT DISCUSSION AND ANALYSIS
        Revenue grew strongly across core segments.
        Margin improved during the year.

        RISK FACTORS
        Supply chain concentration remains a key risk.
        """
        spans = MOD.extract_target_sections(Path("ABC_report.pdf"), sample, "ABC")
        sections = [s.section for s in spans]
        self.assertIn("mda", sections)
        self.assertIn("risk", sections)

    def test_chunk_records_include_metadata(self):
        spans = [
            MOD.SectionSpan(
                file_path=Path("18-02-26_742am_ABC_half-year-results_2A123456.pdf"),
                company="ABC",
                section="cashflow_commentary",
                text="Cash flow remained positive " * 80,
                doc_date="2026-02-18",
            )
        ]
        rows = MOD.build_chunk_records(spans, max_chars=200, overlap_words=10)
        self.assertTrue(rows)
        self.assertTrue(all(r.company == "ABC" for r in rows))
        self.assertTrue(all(r.section == "cashflow_commentary" for r in rows))
        self.assertTrue(all(bool(str(r.title).strip()) for r in rows))
        self.assertTrue(all(r.published_at == "2026-02-18" for r in rows))

    def test_chunk_records_derive_published_at_when_doc_date_missing(self):
        spans = [
            MOD.SectionSpan(
                file_path=Path("18-02-26_742am_ABC_half-year-results_2A123456.pdf"),
                company="ABC",
                section="mda",
                text="Revenue and margins commentary " * 50,
                doc_date="",
            )
        ]
        rows = MOD.build_chunk_records(spans, max_chars=250, overlap_words=10)
        self.assertTrue(rows)
        self.assertTrue(all(bool(str(r.title).strip()) for r in rows))
        self.assertTrue(all(str(r.published_at).startswith("2026-02-18") for r in rows))

    def test_validate_company_symbol_marks_invalid_as_unknown(self):
        company, reason = MOD.validate_company_symbol("ownership_and_holders")
        self.assertEqual(company, "UNKNOWN")
        self.assertEqual(reason, "invalid_company_format")

    def test_validate_company_symbol_checks_allowlist(self):
        company, reason = MOD.validate_company_symbol("BHP", allowlist={"CBA"})
        self.assertEqual(company, "UNKNOWN")
        self.assertEqual(reason, "company_not_in_allowlist")

    def test_chunk_records_preserve_bad_metadata_reason(self):
        spans = [
            MOD.SectionSpan(
                file_path=Path("bad.pdf"),
                company="UNKNOWN",
                section="fulltext_context",
                text="This is extracted from a document with invalid company metadata." * 20,
                doc_date="2026-02-01",
                bad_metadata_reason="invalid_company_format",
            )
        ]
        rows = MOD.build_chunk_records(spans, max_chars=220, overlap_words=20)
        self.assertTrue(rows)
        self.assertTrue(all(r.company == "UNKNOWN" for r in rows))
        self.assertTrue(all(r.bad_metadata_reason == "invalid_company_format" for r in rows))

    def test_store_sqlite_persists_bad_metadata_reason_column(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="company:UNKNOWN:bad:0",
                    company="UNKNOWN",
                    file="bad.pdf",
                    section="fulltext_context",
                    text="bad metadata row",
                    bad_metadata_reason="invalid_company_format",
                )
            ]
            vecs = [MOD.hash_embed(rows[0].text, dim=64)]
            MOD.store_sqlite(rows, vecs, db_path)

            import sqlite3

            conn = sqlite3.connect(str(db_path))
            try:
                cols = [r[1] for r in conn.execute("PRAGMA table_info(context_chunks)").fetchall()]
                self.assertIn("bad_metadata_reason", cols)
                value = conn.execute(
                    "SELECT bad_metadata_reason FROM context_chunks WHERE chunk_id = ?",
                    ("company:UNKNOWN:bad:0",),
                ).fetchone()
                self.assertEqual((value or [""])[0], "invalid_company_format")
            finally:
                conn.close()

    def test_company_validation_gate_threshold_triggers(self):
        records = [
            MOD.ChunkRecord(
                chunk_id=f"c{i}",
                company="UNKNOWN" if i < 3 else "BHP",
                file=f"f{i}.pdf",
                section="fulltext_context",
                text="example text",
                bad_metadata_reason="invalid_company_format" if i < 3 else "",
            )
            for i in range(10)
        ]
        summary = MOD.summarize_company_metadata(records)
        failed, reason = MOD.company_validation_gate_failed(summary, threshold_pct=20.0, min_count=2)
        self.assertTrue(failed)
        self.assertIn("invalid_company_ratio_pct", reason)

    def test_hash_embed_normalized(self):
        vec = MOD.hash_embed("one two three", dim=64)
        norm = sum(x * x for x in vec) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_chunk_ids_do_not_collide_for_multiple_spans_same_section(self):
        spans = [
            MOD.SectionSpan(
                file_path=Path("ABC_report.pdf"),
                company="ABC",
                section="risk",
                text="First risk paragraph " * 30,
            ),
            MOD.SectionSpan(
                file_path=Path("ABC_report.pdf"),
                company="ABC",
                section="risk",
                text="Second risk paragraph " * 30,
            ),
        ]
        rows = MOD.build_chunk_records(spans, max_chars=300, overlap_words=10)
        ids = [r.chunk_id for r in rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hash_embed_deterministic(self):
        a = MOD.hash_embed("cash flow guidance", dim=64)
        b = MOD.hash_embed("cash flow guidance", dim=64)
        self.assertEqual(a, b)

    def test_query_sqlite_returns_company_filtered_rows(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="AAA:1:mda:0",
                    company="AAA",
                    file="AAA_report.pdf",
                    section="mda",
                    text="Revenue and cash flow improved strongly.",
                ),
                MOD.ChunkRecord(
                    chunk_id="BBB:1:risk:0",
                    company="BBB",
                    file="BBB_report.pdf",
                    section="risk",
                    text="Supply chain risk and inflation pressure increased.",
                ),
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="cash flow improvement",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="AAA",
                corpus_filter="",
                doc_type_filter="",
                date_from="",
                date_to="",
                top_k=5,
            )
            self.assertTrue(hits)
            self.assertTrue(all(row["company"] == "AAA" for _, row in hits))

    def test_query_sqlite_corpus_filter(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="company:AAA:a.pdf:risk:0:aaaa",
                    company="AAA",
                    file="a.pdf",
                    section="risk",
                    text="Operating risk and cash flow risk are present.",
                    corpus="company",
                ),
                MOD.ChunkRecord(
                    chunk_id="reference:AAA:b.pdf:risk:0:bbbb",
                    company="AAA",
                    file="b.pdf",
                    section="risk",
                    text="Reference framework for risk and valuation.",
                    corpus="reference",
                ),
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="risk framework",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="AAA",
                corpus_filter="reference",
                doc_type_filter="",
                date_from="",
                date_to="",
                top_k=5,
            )
            self.assertTrue(hits)
            self.assertTrue(all(row["corpus"] == "reference" for _, row in hits))

    def test_extract_full_document_span(self):
        spans = MOD.extract_full_document_span(
            Path("ref.pdf"),
            "Some explanatory text.\n\nMore context.",
            company="REF",
            corpus="reference",
            doc_type="research",
            doc_date="2026-02-21",
        )
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].section, "fulltext_context")
        self.assertEqual(spans[0].corpus, "reference")
        self.assertEqual(spans[0].doc_type, "research")
        self.assertEqual(spans[0].doc_date, "2026-02-21")

    def test_infer_doc_type_announcement_and_textbook(self):
        announcement = MOD.infer_doc_type(Path("18-02-26_1020am_SEG_half-year-fy26-financial-report_3A687354.pdf"), "")
        textbook = MOD.infer_doc_type(Path("Valuation_ Measuring and Managing the V...nies, 5th Edition.pdf"), "")
        self.assertEqual(announcement, "annual_report")
        self.assertEqual(textbook, "textbook")

    def test_infer_doc_date_marketindex_filename(self):
        doc_date = MOD.infer_doc_date(Path("18-02-26_1020am_SEG_half-year-fy26-financial-report_3A687354.pdf"))
        self.assertEqual(doc_date, "2026-02-18")

    def test_derive_company_parses_marketindex_ticker_filename(self):
        pdf_root = Path("/tmp/pdfs")
        pdf = pdf_root / "18-02-26_1020am_SEG_half-year-fy26-financial-report_3A687354.pdf"
        company = MOD.derive_company(pdf, pdf_root)
        self.assertEqual(company, "SEG")

    def test_derive_company_parses_alphanumeric_tickers(self):
        pdf_root = Path("/tmp/pdfs")
        samples = {
            "18-02-26_853am_C79_1h-fy26-results-presentation_2A1654129.pdf": "C79",
            "18-02-26_505pm_GR8_application-for-quotation-of-securities-gr8_6A1312661.pdf": "GR8",
            "18-02-26_815am_5EA_5ea-form-10-q-quarterly-results-31-december-2025_6A1312532.pdf": "5EA",
        }
        for fname, expected in samples.items():
            company = MOD.derive_company(pdf_root / fname, pdf_root)
            self.assertEqual(company, expected)

    def test_derive_company_uses_asx_nested_ticker_directory(self):
        pdf_root = Path("/tmp/asx/docs")
        pdf = pdf_root / "SEG" / "financial_performance" / "2026-02-18_half-year-fy26-results-announcement_x.pdf"
        company = MOD.derive_company(pdf, pdf_root)
        self.assertEqual(company, "SEG")

    def test_ticker_blob_helpers(self):
        blob = MOD.serialize_tickers(["aapl", "MSFT", "aapl", "THISSYMBOLISTOOLONG12345"])
        self.assertEqual(blob, "|AAPL|MSFT|")
        self.assertEqual(MOD.parse_ticker_blob(blob), ["AAPL", "MSFT"])
        self.assertTrue(MOD.ticker_blob_contains(blob, "aapl"))
        self.assertFalse(MOD.ticker_blob_contains(blob, "TSLA"))

    def test_query_sqlite_source_and_ticker_filters(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "news.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="news:reuters:aapl:1",
                    company="AAPL",
                    file="news://1",
                    section="fulltext_context",
                    text="Apple shares rose after stronger than expected iPhone demand.",
                    corpus="news",
                    doc_type="news_article",
                    doc_date="2026-02-15",
                    source="Reuters",
                    ticker=MOD.serialize_tickers(["AAPL"]),
                    topic="earnings",
                    url="https://example.com/apple",
                    title="Apple rises on iPhone demand",
                    published_at="2026-02-15T09:30:00Z",
                ),
                MOD.ChunkRecord(
                    chunk_id="news:cnbc:tsla:1",
                    company="TSLA",
                    file="news://2",
                    section="fulltext_context",
                    text="Tesla shares fell after guidance was trimmed.",
                    corpus="news",
                    doc_type="news_article",
                    doc_date="2026-02-15",
                    source="CNBC",
                    ticker=MOD.serialize_tickers(["TSLA"]),
                    topic="guidance",
                    url="https://example.com/tesla",
                    title="Tesla drops on lower guidance",
                    published_at="2026-02-15T10:00:00Z",
                ),
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="iphone demand",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="",
                corpus_filter="news",
                doc_type_filter="news_article",
                date_from="2026-02-01",
                date_to="2026-02-28",
                top_k=5,
                ticker_filter="AAPL",
                source_filter="Reuters",
            )
            self.assertTrue(hits)
            self.assertTrue(all(row["source"] == "Reuters" for _, row in hits))
            self.assertTrue(all(MOD.ticker_blob_contains(row["ticker"], "AAPL") for _, row in hits))

    def test_query_sqlite_exclude_corpus_filter(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="company:AAA:1",
                    company="AAA",
                    file="a.pdf",
                    section="risk",
                    text="Company filing discusses risk controls.",
                    corpus="company",
                ),
                MOD.ChunkRecord(
                    chunk_id="news:AAA:1",
                    company="AAA",
                    file="news://a",
                    section="fulltext_context",
                    text="News article discusses risk controls.",
                    corpus="news",
                    doc_type="news_article",
                    ticker=MOD.serialize_tickers(["AAA"]),
                    source="Reuters",
                ),
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="risk controls",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="AAA",
                corpus_filter="",
                doc_type_filter="",
                date_from="",
                date_to="",
                top_k=5,
                exclude_corpus_filter="news",
            )
            self.assertTrue(hits)
            self.assertTrue(all(row["corpus"] != "news" for _, row in hits))

    def test_query_sqlite_reranks_results_announcement_over_dividend(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            shared_text = "Half year update and management guidance for operations."
            rows = [
                MOD.ChunkRecord(
                    chunk_id="seg:results:1",
                    company="SEG",
                    file="18-02-26_1020am_SEG_half-year-fy26-results-announcement_3A687351.pdf",
                    section="fulltext_context",
                    text=shared_text,
                    corpus="company",
                    doc_type="announcement",
                ),
                MOD.ChunkRecord(
                    chunk_id="seg:dividend:1",
                    company="SEG",
                    file="18-02-26_1020am_SEG_dividend-distribution-seg_3A687353.pdf",
                    section="fulltext_context",
                    text=shared_text,
                    corpus="company",
                    doc_type="announcement",
                ),
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="SEG half year results announcement guidance",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="SEG",
                corpus_filter="company",
                doc_type_filter="announcement",
                date_from="",
                date_to="",
                top_k=2,
            )
            self.assertTrue(hits)
            self.assertIn("results-announcement", hits[0][1]["file"])

    def test_query_sqlite_doc_type_fallback_accepts_announcement_like_filename(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as td:
            db_path = Path(td) / "ctx.sqlite"
            rows = [
                MOD.ChunkRecord(
                    chunk_id="seg:annualish:1",
                    company="SEG",
                    file="18-02-26_1021am_SEG_half-year-fy26-results-announcement_3A687355.pdf",
                    section="fulltext_context",
                    text="Half year results and guidance update.",
                    corpus="company",
                    doc_type="annual_report",
                )
            ]
            vecs = [MOD.hash_embed(r.text, dim=64) for r in rows]
            MOD.store_sqlite(rows, vecs, db_path)

            hits = MOD.query_sqlite(
                db_path=db_path,
                query="SEG half year results announcement guidance",
                backend="hash",
                model_name="",
                ollama_endpoint="http://127.0.0.1:11434",
                hash_dim=64,
                st_device="auto",
                st_batch_size=16,
                company="SEG",
                corpus_filter="company",
                doc_type_filter="announcement",
                date_from="",
                date_to="",
                top_k=3,
            )
            self.assertTrue(hits)
            self.assertIn("results-announcement", hits[0][1]["file"])

    def test_lexical_rerank_bonus_prefers_results_announcement_over_dividend(self):
        query = "SEG half year results announcement guidance"
        dividend_row = {
            "file": "18-02-26_1020am_SEG_dividend-distribution-seg_3A687353.pdf",
            "section": "fulltext_context",
            "doc_type": "announcement",
            "title": "",
            "topic": "",
        }
        results_row = {
            "file": "18-02-26_1021am_SEG_half-year-fy26-results-announcement_3A687355.pdf",
            "section": "cashflow_commentary",
            "doc_type": "annual_report",
            "title": "",
            "topic": "",
        }

        div_bonus = MOD.lexical_rerank_bonus(query, dividend_row)
        res_bonus = MOD.lexical_rerank_bonus(query, results_row)

        self.assertLess(div_bonus, 0.0)
        self.assertGreater(res_bonus, div_bonus)

    def test_choose_st_device_cuda_strict_raises_when_no_cuda(self):
        torch_stub = types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                is_available=lambda: False,
                device_count=lambda: 0,
                get_device_capability=lambda _idx: (0, 0),
            )
        )
        with mock.patch.dict(sys.modules, {"torch": torch_stub}):
            with self.assertRaises(RuntimeError):
                MOD.choose_sentence_transformers_device("cuda_strict")

    def test_choose_st_device_cuda_strict_returns_cuda_when_available(self):
        torch_stub = types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                is_available=lambda: True,
                device_count=lambda: 1,
                get_device_capability=lambda _idx: (7, 5),
            )
        )
        with mock.patch.dict(sys.modules, {"torch": torch_stub}):
            self.assertEqual(MOD.choose_sentence_transformers_device("cuda_strict"), "cuda")


if __name__ == "__main__":
    unittest.main()
