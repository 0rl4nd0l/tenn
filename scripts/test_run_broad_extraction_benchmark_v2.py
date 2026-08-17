"""Focused safety tests for the issue 554 v2 benchmark runner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest
from unittest import mock

from scripts import run_broad_extraction_benchmark_v2 as RUNNER


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
            )
            with (
                mock.patch.object(
                    RUNNER,
                    "validate_bundle",
                    return_value={
                        "cases": [{}] * 20,
                        "input_sha256": {},
                        "corpus_digest": "c",
                        "contract_digest": "e",
                    },
                ),
                mock.patch.object(RUNNER, "inspect_interpreter", return_value={}),
                mock.patch.object(
                    RUNNER, "require_atomic_publish_capability"
                ) as atomic_capability,
            ):
                self.assertEqual(0, RUNNER._validate_only(args))
            atomic_capability.assert_called_once_with(job)
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
            )
            with (
                mock.patch.object(RUNNER, "validate_bundle", return_value={}),
                mock.patch.object(RUNNER, "inspect_interpreter", return_value={}),
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
        }
        completed = subprocess.CompletedProcess(
            [sys.executable], 0, stdout=json.dumps(payload), stderr=""
        )
        with mock.patch.object(RUNNER.subprocess, "run", return_value=completed):
            inspected = RUNNER.inspect_interpreter(Path(sys.executable))
        self.assertEqual(RUNNER.EXPECTED_DEPENDENCY_VERSIONS, inspected["versions"])
        self.assertIn("binary_sha256", inspected)
        self.assertIn("dependency_snapshot_sha256", inspected)

        payload["versions"]["httpx"] = "0.28.0"
        completed.stdout = json.dumps(payload)
        with (
            mock.patch.object(RUNNER.subprocess, "run", return_value=completed),
            self.assertRaisesRegex(RUNNER.RunnerError, "dependency versions mismatch"),
        ):
            RUNNER.inspect_interpreter(Path(sys.executable))

    def _mock_run(self, *, result_count: int) -> tuple[int, Path, Path, int]:
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
        )

        def replay(command: list[str], **_kwargs: object) -> object:
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
                    "status": "PASS",
                    "results": results,
                },
            )
            write_json(replay_root / "validation.json", {"side_effect_pass": True})
            write_json(
                replay_root / "side_effect_audit.json",
                {"forbidden_surface_clean": True},
            )
            return subprocess.CompletedProcess(command, 0)

        with (
            mock.patch.object(RUNNER, "validate_bundle", return_value=bundle),
            mock.patch.object(RUNNER, "inspect_interpreter", return_value={"ok": True}),
            mock.patch.object(RUNNER.subprocess, "run", side_effect=replay),
            mock.patch.object(
                RUNNER, "score_benchmark", wraps=RUNNER.score_benchmark
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


if __name__ == "__main__":
    unittest.main()
