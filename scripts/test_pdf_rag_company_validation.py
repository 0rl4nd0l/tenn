import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
RAG = load_module(str(ROOT / "scripts" / "pdf_rag.py"), "pdf_rag_company_validation")


class _CtxStub:
    @staticmethod
    def derive_company(pdf, pdf_root):  # noqa: ANN001, ARG002
        return "ownership_and_holders"

    @staticmethod
    def validate_company_symbol(raw_company, allowlist=None):  # noqa: ANN001, ARG002
        return "UNKNOWN", "invalid_company_format"

    @staticmethod
    def infer_doc_type(pdf, text):  # noqa: ANN001, ARG002
        return "announcement"

    @staticmethod
    def infer_doc_date(pdf):  # noqa: ANN001
        return "2026-02-01"

    @staticmethod
    def extract_target_sections(pdf, text, company, bad_metadata_reason=""):  # noqa: ANN001, ARG002
        return [
            SimpleNamespace(
                file_path=pdf,
                company=company,
                section="mda",
                text="content",
                corpus="company",
                doc_type="other",
                doc_date="",
                bad_metadata_reason=bad_metadata_reason,
            )
        ]


class _SyncCtxStub(_CtxStub):
    @staticmethod
    def extract_full_document_span(file_path, text, company, corpus, doc_type, doc_date, bad_metadata_reason=""):  # noqa: ANN001, ARG002
        return [
            SimpleNamespace(
                file_path=file_path,
                company=company,
                section="fulltext_context",
                text="full content",
                corpus=corpus,
                doc_type=doc_type,
                doc_date=doc_date,
                bad_metadata_reason=bad_metadata_reason,
            )
        ]

    @staticmethod
    def build_chunk_records(spans, max_chars=1200, overlap_words=60):  # noqa: ANN001, ARG002
        return [
            SimpleNamespace(
                chunk_id="company:UNKNOWN:test:0",
                company="UNKNOWN",
                file=str(spans[0].file_path),
                section="fulltext_context",
                text="chunk text",
                corpus="company",
                doc_type="announcement",
                doc_date="2026-02-01",
                source="",
                ticker="",
                topic="",
                url="",
                title="",
                published_at="",
                bad_metadata_reason="invalid_company_format",
            )
        ]

    @staticmethod
    def summarize_company_metadata(records):  # noqa: ANN001
        return {
            "total_chunks": len(records),
            "invalid_company_count": 1,
            "invalid_company_ratio_pct": 100.0,
            "company_distribution_top": [{"company": "UNKNOWN", "count": 1}],
            "invalid_reasons": {"invalid_company_format": 1},
        }

    @staticmethod
    def company_validation_gate_failed(summary, threshold_pct, min_count):  # noqa: ANN001
        return True, "invalid_company_ratio_pct=100.0 threshold_pct=1.0 invalid_company_count=1 min_count=1"

    @staticmethod
    def embed_texts(texts, backend, model_name, ollama_endpoint, hash_dim, st_device, st_batch_size):  # noqa: ANN001, ARG002
        return [[0.1] for _ in texts]

    @staticmethod
    def store_sqlite(records, vectors, db_path):  # noqa: ANN001, ARG002
        return None


class PdfRagCompanyValidationTests(unittest.TestCase):
    def test_collect_spans_for_pdf_marks_invalid_company(self):
        ctx = _CtxStub()
        with mock.patch.object(RAG, "extract_pdf_text", return_value="Sample text"):
            spans = RAG.collect_spans_for_pdf(
                ctx=ctx,
                pdf=Path("/tmp/sample.pdf"),
                pdf_root=Path("/tmp"),
                content_scope="targeted",
                fallback_fulltext=False,
                company_allowlist=None,
            )
        self.assertTrue(spans)
        self.assertEqual(spans[0].company, "UNKNOWN")
        self.assertEqual(spans[0].bad_metadata_reason, "invalid_company_format")

    def test_sync_vector_store_raises_when_company_gate_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "sample.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            db_path = root / "rag.sqlite"

            with (
                mock.patch.object(RAG, "load_context_module", return_value=_SyncCtxStub()),
                mock.patch.object(RAG, "find_pdfs", return_value=[pdf]),
                mock.patch.object(RAG, "extract_pdf_text", return_value="Sample text"),
            ):
                with self.assertRaises(RuntimeError) as ctx_exc:
                    RAG.sync_vector_store(
                        pdf_root=root,
                        db_path=db_path,
                        rebuild=True,
                        content_scope="fulltext",
                        fallback_fulltext=False,
                        max_chars=1200,
                        overlap_words=60,
                        embed_backend="hash",
                        embed_model="hash",
                        ollama_endpoint="http://127.0.0.1:11434",
                        hash_dim=64,
                        st_device="cpu",
                        st_batch_size=8,
                        company_allowlist_path="",
                        invalid_company_fail_threshold_pct=1.0,
                        invalid_company_fail_min_count=1,
                    )
            self.assertIn("Company validation gate failed", str(ctx_exc.exception))


if __name__ == "__main__":
    unittest.main()
