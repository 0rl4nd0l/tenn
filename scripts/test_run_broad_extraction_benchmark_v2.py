"""Focused safety tests for the issue 554 v2 benchmark runner."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import types
import unittest
from unittest import mock

from scripts import run_broad_extraction_benchmark_v2 as RUNNER

sys.path.insert(0, str(RUNNER.BACKEND_ROOT))
from app.services import broad_extraction_benchmark as TEST_BENCHMARK  # noqa: E402

RUNNER.bind_benchmark_module(TEST_BENCHMARK)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def build_bundle(root: Path) -> dict[str, object]:
    source_root = root / "source"
    corpus_path = root / "corpus.json"
    expectations_path = root / "expectations.json"
    case_manifest_path = root / "cases.json"
    source_manifest_path = root / "source_manifest.json"
    documents = []
    expectation_documents = []
    cases = []
    source_paths = []
    for index in range(20):
        ticker = f"T{index:02d}"
        document_id = f"doc_{index:02d}"
        relative = f"asx/docs/{ticker}/report.pdf"
        source = source_root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(f"source-{index}".encode())
        source_hash = RUNNER._sha256(source)
        documents.append(
            {
                "document_id": document_id,
                "issuer_id": ticker,
                "document_class": "annual_report",
                "period_type": "A",
                "period_end": "2025-06-30",
                "admission_status": "admitted",
                "source_path": relative,
                "source_sha256": source_hash,
            }
        )
        expectation_documents.append(
            {
                "document_id": document_id,
                "verified": {},
                "unresolved_metrics": list(RUNNER.METRICS),
            }
        )
        cases.append(
            {
                "case_id": f"CASE_{index:02d}",
                "ticker": ticker,
                "document_id": document_id,
                "title": f"{ticker} report",
                "source_path": relative,
                "skip_narrative": True,
            }
        )
        source_paths.append(source)
    corpus = {
        "artifact_type": "broad_extraction_benchmark_corpus_v2",
        "documents": documents,
    }
    expectations = {
        "artifact_type": "broad_extraction_benchmark_expectations_v2",
        "metrics": list(RUNNER.METRICS),
        "documents": expectation_documents,
    }
    cases_payload = {
        "artifact_type": "extraction_no_write_case_manifest_v2",
        "certification": {
            "allow_production_writes": False,
            "loopback_llm_only": True,
            "source_contract": "financial-engine_v2/data/broad_extraction_benchmark/v2/corpus.json",
        },
        "cases": cases,
    }
    write_json(corpus_path, corpus)
    write_json(expectations_path, expectations)
    write_json(case_manifest_path, cases_payload)
    loaded_documents, loaded_expectations = RUNNER._load_contract(corpus, expectations)
    digests = RUNNER._contract_digests(loaded_documents, loaded_expectations)
    source_manifest = {
        "artifact_type": "broad_extraction_benchmark_source_manifest_v2",
        "predecessor": {"preserved": True},
        "successor": {
            "corpus_sha256": RUNNER._sha256(corpus_path),
            "expectations_sha256": RUNNER._sha256(expectations_path),
            "case_manifest_sha256": RUNNER._sha256(case_manifest_path),
            "semantic_corpus_digest": digests["corpus"],
            "semantic_contract_digest": digests["contract"],
        },
    }
    write_json(source_manifest_path, source_manifest)
    hashes = {
        "corpus": RUNNER._sha256(corpus_path),
        "expectations": RUNNER._sha256(expectations_path),
        "case_manifest": RUNNER._sha256(case_manifest_path),
        "source_manifest": RUNNER._sha256(source_manifest_path),
    }
    return {
        "source_root": source_root,
        "corpus_path": corpus_path,
        "expectations_path": expectations_path,
        "case_manifest_path": case_manifest_path,
        "source_manifest_path": source_manifest_path,
        "hashes": hashes,
        "digests": digests,
        "source_paths": source_paths,
        "cases": cases,
    }


class OneShotSafetyTests(unittest.TestCase):
    def test_receipt_creation_is_atomic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = Path(directory) / "INVOCATION_RECEIPT.json"
            barrier = threading.Barrier(2)
            outcomes: list[str] = []

            def create() -> None:
                barrier.wait()
                try:
                    RUNNER.create_invocation_receipt(receipt, {"invocation": "one"})
                except RUNNER.RunnerError:
                    outcomes.append("rejected")
                else:
                    outcomes.append("created")

            threads = [threading.Thread(target=create) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            self.assertCountEqual(["created", "rejected"], outcomes)
            self.assertEqual({"invocation": "one"}, json.loads(receipt.read_text()))

    def test_atomic_publish_never_replaces_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            output = root / "output"
            stage.mkdir()
            output.mkdir()
            (stage / "new.json").write_text("new", encoding="utf-8")
            (output / "sentinel.json").write_text("old", encoding="utf-8")

            with self.assertRaises(RUNNER.RunnerError):
                RUNNER.atomic_publish(stage, output)

            self.assertEqual("old", (output / "sentinel.json").read_text())
            self.assertTrue((stage / "new.json").is_file())

    def test_atomic_publish_capability_probes_exact_output_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_parent = Path(directory)
            with mock.patch.object(
                RUNNER.tempfile,
                "TemporaryDirectory",
                wraps=tempfile.TemporaryDirectory,
            ) as temporary_directory:
                RUNNER.require_atomic_publish_capability(output_parent)

            self.assertEqual(output_parent, temporary_directory.call_args.kwargs["dir"])
            self.assertEqual([], list(output_parent.iterdir()))

    def test_atomic_publish_capability_creates_fresh_output_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_parent = Path(directory) / "new-job"

            RUNNER.require_atomic_publish_capability(output_parent)

            self.assertTrue(output_parent.is_dir())
            self.assertEqual([], list(output_parent.iterdir()))

    def test_atomic_publish_capability_rejects_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            output_parent = root / "job"
            target.mkdir()
            output_parent.symlink_to(target, target_is_directory=True)

            with self.assertRaisesRegex(RUNNER.RunnerError, "must not be a symlink"):
                RUNNER.require_atomic_publish_capability(output_parent)

            self.assertEqual([], list(target.iterdir()))

    def test_atomic_publish_capability_rejects_missing_no_replace_semantics(
        self,
    ) -> None:
        def replacing_rename(
            _old_dir_fd: int,
            source: bytes,
            _new_dir_fd: int,
            destination: bytes,
            _flags: int,
        ) -> int:
            os.replace(source, destination)
            return 0

        with tempfile.TemporaryDirectory() as directory:
            output_parent = Path(directory)
            with (
                mock.patch.object(
                    RUNNER, "_renameat2_function", return_value=replacing_rename
                ),
                self.assertRaisesRegex(
                    RUNNER.RunnerError, "existing directory was replaced"
                ),
            ):
                RUNNER.require_atomic_publish_capability(output_parent)

            self.assertEqual([], list(output_parent.iterdir()))

    def test_complete_results_require_all_twenty_declared_cases(self) -> None:
        cases = [
            {"case_id": f"CASE_{index}", "document_id": f"doc_{index}"}
            for index in range(20)
        ]
        replay = {
            "artifact_type": "extraction_no_write_replay_results_v2",
            "results": [
                {
                    "case_id": row["case_id"],
                    "document_id": row["document_id"],
                    "result": {},
                }
                for row in cases[:-1]
            ],
        }

        with self.assertRaisesRegex(RUNNER.RunnerError, "all 20"):
            RUNNER.require_complete_results(cases, replay)

    def test_existing_output_or_receipt_fails_without_consuming_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            receipt = root / "INVOCATION_RECEIPT.json"
            output.mkdir()
            with self.assertRaisesRegex(
                RUNNER.RunnerError, "output root already exists"
            ):
                RUNNER.require_fresh_authority(output, receipt)
            output.rmdir()
            receipt.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RUNNER.RunnerError, "receipt already exists"):
                RUNNER.require_fresh_authority(output, receipt)

    def test_dangling_output_symlink_is_existing_authority_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output"
            output.symlink_to(root / "missing-target", target_is_directory=True)

            with self.assertRaisesRegex(
                RUNNER.RunnerError, "output root already exists"
            ):
                RUNNER.require_fresh_authority(output, root / "INVOCATION_RECEIPT.json")
            with self.assertRaisesRegex(RUNNER.RunnerError, "refusing symlink"):
                RUNNER._normalize_report_path(output)

    def test_results_require_v2_artifact_and_result_object_for_every_row(self) -> None:
        cases = [
            {"case_id": f"CASE_{index}", "document_id": f"doc_{index}"}
            for index in range(20)
        ]
        results = [
            {
                "case_id": row["case_id"],
                "document_id": row["document_id"],
                "result": {},
            }
            for row in cases
        ]
        with self.assertRaisesRegex(RUNNER.RunnerError, "artifact_type"):
            RUNNER.require_complete_results(cases, {"results": results})
        results[0]["result"] = None
        with self.assertRaisesRegex(RUNNER.RunnerError, "result object"):
            RUNNER.require_complete_results(
                cases,
                {
                    "artifact_type": "extraction_no_write_replay_results_v2",
                    "results": results,
                },
            )

    def test_total_debt_uses_benchmark_internal_observation(self) -> None:
        document = RUNNER.CorpusDocument(
            document_id="doc_0",
            issuer_id="T00",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path="source_0.pdf",
            source_sha256="1" * 64,
        )
        replay = {
            "results": [
                {
                    "document_id": "doc_0",
                    "result": {
                        "status": "ok",
                        "period_type": "A",
                        "period_end": "2025-06-30",
                        "currency": "AUD",
                        "benchmark_internal_metrics": {"total_debt": 25_000_000},
                        "benchmark_internal_metric_source_scales": {
                            "total_debt": "millions"
                        },
                        "benchmark_internal_provenance": {
                            "total_debt": "balance_sheet:page_12:Borrowings"
                        },
                        "benchmark_internal_source_cells": {
                            "total_debt": {
                                "raw_value": "25",
                                "scaled_value": 25_000_000,
                                "requested_period_end": "2025-06-30",
                            }
                        },
                    },
                }
            ]
        }

        actuals = RUNNER.actuals_from_replay((document,), replay)
        total_debt = next(row for row in actuals if row.metric == "total_debt")

        self.assertEqual("accepted", total_debt.status)
        self.assertEqual("25", total_debt.raw_value)
        self.assertEqual("25000000", total_debt.normalized_value)
        self.assertEqual(
            "balance_sheet:page_12:Borrowings", total_debt.evidence_location
        )

        replay["results"][0]["result"]["benchmark_internal_source_cells"]["total_debt"][
            "requested_period_end"
        ] = "2024-06-30"
        mismatched = RUNNER.actuals_from_replay((document,), replay)
        total_debt = next(row for row in mismatched if row.metric == "total_debt")
        self.assertEqual("abstained", total_debt.status)

    def test_low_confidence_success_is_scoreable(self) -> None:
        document = RUNNER.CorpusDocument(
            document_id="doc_0",
            issuer_id="T00",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path="source_0.pdf",
            source_sha256="1" * 64,
        )
        replay = {
            "results": [
                {
                    "document_id": "doc_0",
                    "result": {
                        "status": "ok_low_confidence",
                        "period_type": "A",
                        "period_end": "2025-06-30",
                        "currency": "USD",
                        "non_null_metrics": {"revenue": 25_000_000},
                        "metric_source_scales": {"revenue": "millions"},
                        "provenance": {"revenue": "income:page_8:Revenue"},
                        "benchmark_metric_source_cells": {
                            "revenue": {
                                "raw_value": "0.025bn",
                                "scaled_value": 25_000_000,
                                "requested_period_end": "2025-06-30",
                            }
                        },
                    },
                }
            ]
        }

        actuals = RUNNER.actuals_from_replay((document,), replay)
        revenue = next(row for row in actuals if row.metric == "revenue")

        self.assertEqual("accepted", revenue.status)
        self.assertEqual("USD", revenue.currency)
        self.assertEqual("0.025", revenue.raw_value)
        self.assertEqual("billions", revenue.raw_unit)

        replay["results"][0]["result"]["currency"] = "AUD"
        replay["results"][0]["result"]["benchmark_metric_source_cells"]["revenue"][
            "raw_value"
        ] = "US$25m"
        explicit_currency = RUNNER.actuals_from_replay((document,), replay)
        revenue = next(row for row in explicit_currency if row.metric == "revenue")
        self.assertEqual("accepted", revenue.status)
        self.assertEqual("USD", revenue.currency)
        self.assertEqual("25", revenue.raw_value)
        self.assertEqual("millions", revenue.raw_unit)

    def test_shares_preserve_period_bound_raw_source_identity(self) -> None:
        document = RUNNER.CorpusDocument(
            document_id="doc_0",
            issuer_id="T00",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path="source_0.pdf",
            source_sha256="1" * 64,
        )
        payload = {
            "status": "ok",
            "period_type": "A",
            "period_end": "2025-06-30",
            "non_null_metrics": {"shares_outstanding": 2_945_000_000},
            "metric_source_scales": {"shares_outstanding": "millions"},
            "provenance": {
                "shares_outstanding": "share_capital:page_22:Ordinary shares"
            },
            "benchmark_metric_source_cells": {
                "shares_outstanding": {
                    "raw_value": "2,945 million",
                    "scaled_value": 2_945_000_000,
                    "requested_period_end": "2025-06-30",
                }
            },
        }
        replay = {"results": [{"document_id": "doc_0", "result": payload}]}

        actuals = RUNNER.actuals_from_replay((document,), replay)
        shares = next(row for row in actuals if row.metric == "shares_outstanding")
        self.assertEqual("accepted", shares.status)
        self.assertEqual("2945", shares.raw_value)
        self.assertEqual("millions", shares.raw_unit)
        self.assertEqual("2945000000", shares.normalized_value)

        payload["benchmark_metric_source_cells"]["shares_outstanding"][
            "requested_period_end"
        ] = "2024-06-30"
        mismatched = RUNNER.actuals_from_replay((document,), replay)
        shares = next(row for row in mismatched if row.metric == "shares_outstanding")
        self.assertEqual("abstained", shares.status)

        payload["benchmark_metric_source_cells"] = {}
        missing = RUNNER.actuals_from_replay((document,), replay)
        shares = next(row for row in missing if row.metric == "shares_outstanding")
        self.assertEqual("abstained", shares.status)

    def test_produced_share_source_cell_survives_compaction_and_scores(self) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _apply_preferred_shares_source_payload,
        )
        from scripts import extraction_no_write_replay as REPLAY

        table = DoclingTable(
            page_number=22,
            caption="Number of shares millions",
            headers=["", "30 June 2025", "30 June 2024"],
            raw_header_rows=[["", "30 June 2025", "30 June 2024"]],
            rows=[
                [
                    "Issued ordinary shares fully paid at 30 June 2025",
                    "2,945",
                    "2,900",
                ]
            ],
        )
        payload = {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "metrics": {"shares_outstanding": None},
            "shares_outstanding": None,
            "row_refs": {},
            "provenance": {},
        }
        _apply_preferred_shares_source_payload(
            payload,
            [table],
            pass1_result={
                "report_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
            },
            capture_benchmark_source_cell=True,
        )

        compacted = REPLAY._compact_payload(
            types.SimpleNamespace(status="ok", error=None, payload=payload),
            benchmark_internal_metrics={
                "values": {},
                "metric_source_scales": {},
                "metric_scale_sources": {},
                "provenance": {},
                "source_cells": {},
            },
        )
        document = RUNNER.CorpusDocument(
            document_id="doc_0",
            issuer_id="T00",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path="source_0.pdf",
            source_sha256="1" * 64,
        )
        actuals = RUNNER.actuals_from_replay(
            (document,),
            {"results": [{"document_id": "doc_0", "result": compacted}]},
        )
        shares = next(row for row in actuals if row.metric == "shares_outstanding")

        self.assertEqual("accepted", shares.status)
        self.assertEqual("2945", shares.raw_value)
        self.assertEqual("millions", shares.raw_unit)
        self.assertEqual("2945000000", shares.normalized_value)
        self.assertEqual(
            "2025-06-30",
            compacted["benchmark_metric_source_cells"]["shares_outstanding"][
                "requested_period_end"
            ],
        )

    def test_income_and_cash_cells_survive_compaction_without_runner_changes(
        self,
    ) -> None:
        from app.services.docling_extract import DoclingTable
        from app.services.multipass_extraction import (
            _apply_preferred_cash_end_source_payload,
            _apply_preferred_income_statement_source_payload,
            _prune_unbound_benchmark_source_cells,
        )
        from scripts import extraction_no_write_replay as REPLAY

        income = DoclingTable(
            page_number=111,
            caption="Consolidated Income Statement",
            headers=["", "30 June 2025 $M", "30 June 2024 $M"],
            raw_header_rows=[["", "30 June 2025", "30 June 2024"]],
            rows=[["Revenue", "69,077", "67,922"]],
        )
        cashflow = DoclingTable(
            page_number=115,
            caption="Consolidated statement of cash flows",
            headers=["", "30 June 2025 $M", "30 June 2024 $M"],
            raw_header_rows=[["", "30 June 2025", "30 June 2024"]],
            rows=[
                [
                    "Cash and cash equivalents at the end of the financial year",
                    "1,275",
                    "1,036",
                ]
            ],
        )
        payload = {
            "period_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
            "scale": "millions",
            "metrics": {"revenue": 69_077_000_000, "cash_end": None},
            "revenue": 69_077_000_000,
            "cash_end": None,
            "row_refs": {"revenue": "Revenue"},
            "provenance": {
                "revenue": "income_statement:page_111:Revenue"
            },
            "field_provenance": {
                "revenue": {
                    "metric": "revenue",
                    "source": "income_statement",
                    "row_ref": "Revenue",
                }
            },
            "metric_source_scales": {"revenue": "millions"},
            "metric_scale_sources": {"revenue": "table"},
        }
        pass1 = {
            "report_type": "A",
            "period_end": "2025-06-30",
            "currency": "AUD",
        }
        _apply_preferred_income_statement_source_payload(
            payload,
            [income],
            scale="millions",
            pass1_result=pass1,
            capture_benchmark_source_cell=True,
        )
        _apply_preferred_cash_end_source_payload(
            payload,
            [cashflow],
            scale="millions",
            pass1_result=pass1,
            capture_benchmark_source_cell=True,
        )
        _prune_unbound_benchmark_source_cells(payload)

        compacted = REPLAY._compact_payload(
            types.SimpleNamespace(status="ok", error=None, payload=payload),
            benchmark_internal_metrics={
                "values": {},
                "metric_source_scales": {},
                "metric_scale_sources": {},
                "provenance": {},
                "source_cells": {},
            },
        )
        document = RUNNER.CorpusDocument(
            document_id="doc_0",
            issuer_id="T00",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path="source_0.pdf",
            source_sha256="1" * 64,
        )

        actuals = RUNNER.actuals_from_replay(
            (document,),
            {"results": [{"document_id": "doc_0", "result": compacted}]},
        )
        revenue = next(row for row in actuals if row.metric == "revenue")
        cash = next(row for row in actuals if row.metric == "cash_and_equivalents")

        self.assertEqual("accepted", revenue.status)
        self.assertEqual("69077", revenue.raw_value)
        self.assertEqual("accepted", cash.status)
        self.assertEqual("1275", cash.raw_value)

    def test_exact_v2_bundle_accepts_all_twenty_declared_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle(Path(directory))
            with (
                mock.patch.dict(
                    RUNNER.EXPECTED_INPUT_SHA256, bundle["hashes"], clear=True
                ),
                mock.patch.dict(
                    RUNNER.EXPECTED_SEMANTIC_DIGESTS, bundle["digests"], clear=True
                ),
            ):
                validated = RUNNER.validate_bundle(
                    corpus_path=bundle["corpus_path"],
                    expectations_path=bundle["expectations_path"],
                    source_manifest_path=bundle["source_manifest_path"],
                    case_manifest_path=bundle["case_manifest_path"],
                    source_root=bundle["source_root"],
                )

            self.assertEqual(20, len(validated["cases"]))
            self.assertEqual(bundle["digests"]["corpus"], validated["corpus_digest"])

    def test_bundle_rejects_input_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle(Path(directory))
            bundle["case_manifest_path"].write_text("{}\n", encoding="utf-8")
            with (
                mock.patch.dict(
                    RUNNER.EXPECTED_INPUT_SHA256, bundle["hashes"], clear=True
                ),
                mock.patch.dict(
                    RUNNER.EXPECTED_SEMANTIC_DIGESTS, bundle["digests"], clear=True
                ),
                self.assertRaisesRegex(
                    RUNNER.RunnerError, "case_manifest SHA-256 mismatch"
                ),
            ):
                RUNNER.validate_bundle(
                    corpus_path=bundle["corpus_path"],
                    expectations_path=bundle["expectations_path"],
                    source_manifest_path=bundle["source_manifest_path"],
                    case_manifest_path=bundle["case_manifest_path"],
                    source_root=bundle["source_root"],
                )

    def test_bundle_rejects_changed_declared_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle(Path(directory))
            source = bundle["source_paths"][0]
            source.write_bytes(b"changed")
            with (
                mock.patch.dict(
                    RUNNER.EXPECTED_INPUT_SHA256, bundle["hashes"], clear=True
                ),
                mock.patch.dict(
                    RUNNER.EXPECTED_SEMANTIC_DIGESTS, bundle["digests"], clear=True
                ),
                self.assertRaisesRegex(RUNNER.RunnerError, "source SHA-256 mismatch"),
            ):
                RUNNER.validate_bundle(
                    corpus_path=bundle["corpus_path"],
                    expectations_path=bundle["expectations_path"],
                    source_manifest_path=bundle["source_manifest_path"],
                    case_manifest_path=bundle["case_manifest_path"],
                    source_root=bundle["source_root"],
                )

    def test_bundle_rejects_missing_declared_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = build_bundle(Path(directory))
            bundle["source_paths"][0].unlink()
            with (
                mock.patch.dict(
                    RUNNER.EXPECTED_INPUT_SHA256, bundle["hashes"], clear=True
                ),
                mock.patch.dict(
                    RUNNER.EXPECTED_SEMANTIC_DIGESTS, bundle["digests"], clear=True
                ),
                self.assertRaisesRegex(
                    RUNNER.RunnerError, "must be an existing non-symlink regular file"
                ),
            ):
                RUNNER.validate_bundle(
                    corpus_path=bundle["corpus_path"],
                    expectations_path=bundle["expectations_path"],
                    source_manifest_path=bundle["source_manifest_path"],
                    case_manifest_path=bundle["case_manifest_path"],
                    source_root=bundle["source_root"],
                )

    def test_validate_only_never_creates_receipt(self) -> None:
        report_parent = RUNNER.REPO_ROOT / "reports/agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=report_parent) as directory:
            job = Path(directory)
            args = mock.Mock(
                output_root=job / "output",
                receipt_path=job / RUNNER.RECEIPT_NAME,
                corpus=job / "corpus.json",
                expectations=job / "expectations.json",
                source_manifest=job / "source_manifest.json",
                case_manifest=job / "cases.json",
                source_root=job / "sources",
                python_bin=Path(sys.executable),
                llm_base_url="http://127.0.0.1:8001",
                case_timeout_seconds=1,
                expected_git_head="a" * 40,
            )
            events: list[str] = []
            bundle = {
                "cases": [{}] * 20,
                "input_sha256": {},
                "corpus_digest": "c",
                "contract_digest": "e",
            }
            with (
                mock.patch.object(
                    RUNNER,
                    "validate_bundle",
                    side_effect=lambda **_kwargs: events.append("bundle") or bundle,
                ),
                mock.patch.object(RUNNER, "inspect_interpreter", return_value={}),
                mock.patch.object(
                    RUNNER,
                    "inspect_code_identity",
                    side_effect=lambda _head: (
                        events.append("identity") or {"head_sha": "a" * 40}
                    ),
                ),
                mock.patch.object(
                    RUNNER,
                    "load_bound_benchmark_module",
                    side_effect=lambda _binding: (
                        events.append("load") or TEST_BENCHMARK
                    ),
                ),
                mock.patch.object(
                    RUNNER, "require_atomic_publish_capability"
                ) as atomic_capability,
            ):
                self.assertEqual(0, RUNNER._validate_only(args))
            atomic_capability.assert_called_once_with(job)
            self.assertLess(events.index("identity"), events.index("load"))
            self.assertLess(events.index("load"), events.index("bundle"))
            self.assertFalse(args.receipt_path.exists())

    def test_validate_only_cannot_bypass_consumed_sibling_receipt(self) -> None:
        report_parent = RUNNER.REPO_ROOT / "reports/agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=report_parent) as directory:
            job = Path(directory)
            required_receipt = job / RUNNER.RECEIPT_NAME
            required_receipt.write_text("{}\n", encoding="utf-8")
            args = mock.Mock(
                output_root=job / "output",
                receipt_path=job / "unbound-receipt.json",
                llm_base_url="http://127.0.0.1:8001",
                case_timeout_seconds=1,
            )

            with self.assertRaisesRegex(RUNNER.RunnerError, "must be exactly"):
                RUNNER._validate_only(args)

            self.assertEqual("{}\n", required_receipt.read_text(encoding="utf-8"))
            self.assertFalse(args.receipt_path.exists())

    def test_outer_preflight_rejects_url_and_timeout_before_receipt(self) -> None:
        report_parent = RUNNER.REPO_ROOT / "reports/agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=report_parent) as directory:
            job = Path(directory)
            base_args = {
                "output_root": job / "output",
                "receipt_path": job / RUNNER.RECEIPT_NAME,
                "corpus": job / "corpus.json",
                "expectations": job / "expectations.json",
                "source_manifest": job / "source_manifest.json",
                "case_manifest": job / "cases.json",
                "source_root": job / "sources",
                "python_bin": Path(sys.executable),
                "llm_base_url": "https://example.com",
                "case_timeout_seconds": 1,
                "expected_git_head": "a" * 40,
            }
            for changes, message in (
                ({}, "loopback"),
                (
                    {
                        "llm_base_url": "http://127.0.0.1:8001",
                        "case_timeout_seconds": 0,
                    },
                    "positive integer",
                ),
            ):
                args = argparse.Namespace(**(base_args | changes))
                with self.assertRaisesRegex(RUNNER.RunnerError, message):
                    RUNNER._run(args)
                self.assertFalse(args.receipt_path.exists())

    def test_atomic_publish_capability_is_checked_before_receipt(self) -> None:
        report_parent = RUNNER.REPO_ROOT / "reports/agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=report_parent) as directory:
            job = Path(directory)
            receipt = job / RUNNER.RECEIPT_NAME
            args = argparse.Namespace(
                output_root=job / "output",
                receipt_path=receipt,
                corpus=job / "corpus.json",
                expectations=job / "expectations.json",
                source_manifest=job / "source_manifest.json",
                case_manifest=job / "cases.json",
                source_root=job / "sources",
                python_bin=Path(sys.executable),
                llm_base_url="http://127.0.0.1:8001",
                case_timeout_seconds=1,
                expected_git_head="a" * 40,
            )
            with (
                mock.patch.object(RUNNER, "validate_bundle", return_value={}),
                mock.patch.object(RUNNER, "inspect_interpreter", return_value={}),
                mock.patch.object(
                    RUNNER,
                    "inspect_code_identity",
                    return_value={"head_sha": "a" * 40},
                ),
                mock.patch.object(
                    RUNNER,
                    "load_bound_benchmark_module",
                    return_value=TEST_BENCHMARK,
                ),
                mock.patch.object(
                    RUNNER,
                    "require_atomic_publish_capability",
                    side_effect=RUNNER.RunnerError("publication unavailable"),
                ) as atomic_capability,
                self.assertRaisesRegex(RUNNER.RunnerError, "publication unavailable"),
            ):
                RUNNER._run(args)

            atomic_capability.assert_called_once_with(job)
            self.assertFalse(receipt.exists())

    def test_interpreter_preflight_enforces_exact_pinned_versions(self) -> None:
        payload = {
            "executable": sys.executable,
            "python": "3.12.0",
            "modules": list(RUNNER.IMPORT_PREFLIGHT_MODULES),
            "versions": dict(RUNNER.EXPECTED_DEPENDENCY_VERSIONS),
            "site_packages": [str(Path(sys.executable).resolve().parent)],
        }
        completed = subprocess.CompletedProcess(
            [sys.executable], 0, stdout=json.dumps(payload), stderr=""
        )
        with mock.patch.object(
            RUNNER.subprocess, "run", return_value=completed
        ) as subprocess_run:
            inspected = RUNNER.inspect_interpreter(Path(sys.executable))
        self.assertEqual(RUNNER.EXPECTED_DEPENDENCY_VERSIONS, inspected["versions"])
        self.assertIn("binary_sha256", inspected)
        self.assertIn("dependency_snapshot_sha256", inspected)
        probe_code = subprocess_run.call_args.args[0][2]
        self.assertIn("os.path.isdir(p)", probe_code)
        self.assertIn("not os.path.islink(p)", probe_code)

        payload["versions"]["httpx"] = "0.28.0"
        completed.stdout = json.dumps(payload)
        with (
            mock.patch.object(RUNNER.subprocess, "run", return_value=completed),
            self.assertRaisesRegex(RUNNER.RunnerError, "dependency versions mismatch"),
        ):
            RUNNER.inspect_interpreter(Path(sys.executable))

    def test_interpreter_preflight_isolates_import_side_effects(self) -> None:
        payload = {
            "executable": sys.executable,
            "python": "3.12.0",
            "modules": list(RUNNER.IMPORT_PREFLIGHT_MODULES),
            "versions": dict(RUNNER.EXPECTED_DEPENDENCY_VERSIONS),
            "site_packages": [str(Path(sys.executable).resolve().parent)],
        }
        isolated_data_root: Path | None = None

        def simulate_import_side_effect(*args: object, **kwargs: object) -> object:
            nonlocal isolated_data_root
            environment = kwargs["env"]
            assert isinstance(environment, dict)
            isolated_data_root = Path(environment["DATA_ROOT"])
            snapshot = isolated_data_root / "reports/router_metrics_snapshot.json"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text("isolated\n", encoding="utf-8")
            return subprocess.CompletedProcess(
                args[0], 0, stdout=json.dumps(payload), stderr=""
            )

        with tempfile.TemporaryDirectory() as directory:
            live_data_root = Path(directory) / "live-data"
            live_snapshot = live_data_root / "reports/router_metrics_snapshot.json"
            live_snapshot.parent.mkdir(parents=True)
            live_snapshot.write_text("preserve-me\n", encoding="utf-8")
            with (
                mock.patch.dict(
                    os.environ, {"DATA_ROOT": str(live_data_root)}, clear=False
                ),
                mock.patch.object(
                    RUNNER.subprocess, "run", side_effect=simulate_import_side_effect
                ),
            ):
                RUNNER.inspect_interpreter(Path(sys.executable))

            self.assertEqual("preserve-me\n", live_snapshot.read_text(encoding="utf-8"))
            self.assertIsNotNone(isolated_data_root)
            assert isolated_data_root is not None
            self.assertTrue(isolated_data_root.is_absolute())
            self.assertIn("tenn-v2-import-preflight-", isolated_data_root.name)
            self.assertNotEqual(live_data_root.resolve(), isolated_data_root)
            self.assertFalse(isolated_data_root.exists())

    def test_replay_launch_environment_drops_unbound_python_startup_paths(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "PYTHONPATH": "/tmp/unbound-code",
                "PYTHONSTARTUP": "/tmp/unbound-startup.py",
            },
            clear=False,
        ):
            environment = RUNNER.replay_launch_environment()

        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("PYTHONSTARTUP", environment)
        self.assertEqual("1", environment["PYTHONDONTWRITEBYTECODE"])
        self.assertEqual("1", environment["PYTHONSAFEPATH"])

    def test_code_identity_rejects_head_mismatch_and_tracked_dirt(self) -> None:
        expected = "a" * 40
        clean_outputs = iter(["b" * 40, "", "", "c" * 40])
        with (
            mock.patch.object(RUNNER, "_git_output", side_effect=clean_outputs),
            self.assertRaisesRegex(RUNNER.RunnerError, "expected Git HEAD"),
        ):
            RUNNER.inspect_code_identity(expected)

        dirty_outputs = iter([expected, " M scripts/extraction_no_write_replay.py"])
        with (
            mock.patch.object(RUNNER, "_git_output", side_effect=dirty_outputs),
            self.assertRaisesRegex(RUNNER.RunnerError, "tracked worktree"),
        ):
            RUNNER.inspect_code_identity(expected)

    def test_bound_benchmark_loader_ignores_hostile_cached_module(self) -> None:
        hostile = types.ModuleType("app.services.broad_extraction_benchmark")
        hostile.score_benchmark = mock.Mock(side_effect=AssertionError("hostile"))
        runner_path = Path(RUNNER.__file__)
        spec = importlib.util.spec_from_file_location("isolated_v2_runner", runner_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        isolated = importlib.util.module_from_spec(spec)
        with mock.patch.dict(
            sys.modules,
            {"app.services.broad_extraction_benchmark": hostile},
        ):
            spec.loader.exec_module(isolated)

        self.assertEqual((), isolated.METRICS)
        source_path = isolated.REPO_ROOT / isolated.BENCHMARK_MODULE_PATH
        binding = {
            "head_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "tracked_files_sha256": {
                isolated.BENCHMARK_MODULE_PATH: isolated._sha256(source_path)
            },
        }
        with mock.patch.object(isolated, "require_unchanged_code_identity"):
            bound = isolated.load_bound_benchmark_module(binding)
        isolated.bind_benchmark_module(bound)

        self.assertIs(isolated.CorpusDocument, bound.CorpusDocument)
        self.assertEqual(TEST_BENCHMARK.METRICS, isolated.METRICS)
        self.assertIsNot(bound.score_benchmark, hostile.score_benchmark)
        hostile.score_benchmark.assert_not_called()

    def _mock_run(
        self,
        *,
        result_count: int,
        side_effect_pass: bool | None = True,
        replay_status: str = "PASS",
        replay_returncode: int = 0,
        infrastructure_failure_count: int = 0,
        code_identity_drift_after_launch: bool = False,
        child_code_identity_conflict: bool = False,
    ) -> tuple[int, Path, Path, int]:
        report_parent = RUNNER.REPO_ROOT / "reports/agent_jobs"
        report_parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=report_parent)
        self.addCleanup(temporary.cleanup)
        job = Path(temporary.name)
        output = job / "output"
        receipt = job / RUNNER.RECEIPT_NAME
        documents = tuple(
            RUNNER.CorpusDocument(
                document_id=f"doc_{index}",
                issuer_id=f"T{index:02d}",
                document_class="annual_report",
                period_type="A",
                period_end="2025-06-30",
                admission_status="admitted",
                source_path=f"source_{index}.pdf",
                source_sha256=f"{index + 1:064x}",
            )
            for index in range(20)
        )
        expectations = tuple(
            RUNNER.ExpectedCell(
                document_id=document.document_id,
                metric=metric,
                applicability="unresolved",
                adjudication_status="unresolved",
            )
            for document in documents
            for metric in RUNNER.METRICS
        )
        cases = [
            {"case_id": f"CASE_{index}", "document_id": f"doc_{index}"}
            for index in range(20)
        ]
        digests = RUNNER._contract_digests(documents, expectations)
        bundle = {
            "input_sha256": {"case_manifest": "a" * 64, "corpus": "b" * 64},
            "corpus_digest": digests["corpus"],
            "contract_digest": digests["contract"],
            "cases": cases,
            "documents": documents,
            "expectations": expectations,
            "source_manifest": {"predecessor": {"p": 1}, "successor": {"s": 2}},
        }
        args = argparse.Namespace(
            output_root=output,
            receipt_path=receipt,
            corpus=job / "corpus.json",
            expectations=job / "expectations.json",
            source_manifest=job / "source_manifest.json",
            case_manifest=job / "cases.json",
            source_root=job / "sources",
            python_bin=Path(sys.executable),
            llm_base_url="http://127.0.0.1:8001",
            case_timeout_seconds=1,
            expected_git_head="a" * 40,
        )

        def replay(command: list[str], **_kwargs: object) -> object:
            self.assertEqual(["-I", "-B", "-S"], command[1:4])
            self.assertEqual(RUNNER.replay_launch_environment(), _kwargs.get("env"))
            if child_code_identity_conflict:
                return subprocess.CompletedProcess(
                    command, RUNNER.CODE_IDENTITY_CONFLICT_EXIT_CODE
                )
            report_arg = command[command.index("--report-dir") + 1]
            replay_root = RUNNER.REPO_ROOT / report_arg
            results = [
                {
                    "case_id": cases[index]["case_id"],
                    "document_id": cases[index]["document_id"],
                    "result": {"status": "failed"},
                }
                for index in range(result_count)
            ]
            write_json(
                replay_root / "replay_results.json",
                {
                    "artifact_type": "extraction_no_write_replay_results_v2",
                    "status": replay_status,
                    "results": results,
                },
            )
            validation = (
                {}
                if side_effect_pass is None
                else {
                    "status": replay_status,
                    "side_effect_pass": side_effect_pass,
                    "infrastructure_failure_count": infrastructure_failure_count,
                    "llm_info": {},
                }
            )
            write_json(replay_root / "validation.json", validation)
            write_json(
                replay_root / "side_effect_audit.json",
                {"forbidden_surface_clean": True},
            )
            return subprocess.CompletedProcess(command, replay_returncode)

        code_identity = {
            "head_sha": "a" * 40,
            "tree_sha": "b" * 40,
            "tracked_files_sha256": {},
        }
        identity_probe = mock.Mock(return_value=code_identity)
        if code_identity_drift_after_launch:
            changed_identity = code_identity | {"tree_sha": "c" * 40}
            identity_probe.side_effect = [
                code_identity,
                changed_identity,
                code_identity,
            ]

        with (
            mock.patch.object(RUNNER, "validate_bundle", return_value=bundle),
            mock.patch.object(RUNNER, "inspect_interpreter", return_value={"ok": True}),
            mock.patch.object(RUNNER, "inspect_code_identity", identity_probe),
            mock.patch.object(RUNNER.subprocess, "run", side_effect=replay),
            mock.patch.object(
                RUNNER,
                "load_bound_benchmark_module",
                return_value=TEST_BENCHMARK,
            ),
            mock.patch.object(
                TEST_BENCHMARK,
                "score_benchmark",
                wraps=TEST_BENCHMARK.score_benchmark,
            ) as scorer,
        ):
            returncode = RUNNER._run(args)
        return returncode, output, receipt, scorer.call_count

    def test_complete_mock_run_scores_and_atomically_seals_outputs(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(result_count=20)

        self.assertEqual(0, returncode)
        self.assertTrue(receipt.is_file())
        self.assertTrue((output / "baseline_score.json").is_file())
        self.assertTrue((output / "OUTPUT_MANIFEST.json").is_file())
        self.assertTrue((output / "SHA256SUMS").is_file())
        self.assertEqual(1, scorer_calls)
        self.assertEqual(
            "BASELINE_FROZEN_SCORED",
            json.loads((output / "RUN_OUTCOME.json").read_text())["terminal_state"],
        )

    def test_clean_code_identity_switch_is_evidence_conflict_before_scoring(
        self,
    ) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=20,
            code_identity_drift_after_launch=True,
        )

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("EVIDENCE_CONFLICT", outcome["terminal_state"])
        self.assertIn("code identity changed", outcome["error"])

    def test_initial_child_code_identity_conflict_survives_clean_restore(
        self,
    ) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=20,
            child_code_identity_conflict=True,
        )

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("EVIDENCE_CONFLICT", outcome["terminal_state"])
        self.assertIn("before report creation", outcome["error"])

    def test_complete_quality_failure_is_scored(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=20,
            replay_status="FAIL",
            replay_returncode=2,
        )

        self.assertEqual(0, returncode)
        self.assertTrue(receipt.is_file())
        self.assertTrue((output / "baseline_score.json").is_file())
        self.assertEqual(1, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("BASELINE_FROZEN_SCORED", outcome["terminal_state"])

    def test_complete_infrastructure_failure_is_not_scored(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=20,
            replay_status="DATA_MISSING",
            replay_returncode=2,
            infrastructure_failure_count=1,
        )

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("DATA_MISSING", outcome["terminal_state"])
        self.assertIn("infrastructure", outcome["error"])

    def test_missing_result_publishes_consumed_evidence_without_score(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(result_count=19)

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertTrue(output.is_dir())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("DATA_MISSING", outcome["terminal_state"])
        self.assertIn("all 20", outcome["error"])

    def test_side_effect_conflict_outranks_incomplete_results(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=19, side_effect_pass=False
        )

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertTrue(output.is_dir())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("EVIDENCE_CONFLICT", outcome["terminal_state"])
        self.assertEqual("replay side-effect audit failed", outcome["error"])

    def test_missing_side_effect_verdict_is_data_missing(self) -> None:
        returncode, output, receipt, scorer_calls = self._mock_run(
            result_count=19, side_effect_pass=None
        )

        self.assertEqual(2, returncode)
        self.assertTrue(receipt.is_file())
        self.assertTrue(output.is_dir())
        self.assertFalse((output / "baseline_score.json").exists())
        self.assertEqual(0, scorer_calls)
        outcome = json.loads((output / "RUN_OUTCOME.json").read_text())
        self.assertEqual("DATA_MISSING", outcome["terminal_state"])
        self.assertIn("side_effect_pass", outcome["error"])


if __name__ == "__main__":
    unittest.main()
