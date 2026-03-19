import concurrent.futures
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ROOT = Path(__file__).resolve().parents[1]
MOD = load_module(str(ROOT / "scripts" / "run_parallel_extraction.py"), "run_parallel_extraction")


class InlineExecutor:
    last_instance = None

    def __init__(self, max_workers: int):
        self.max_workers = max_workers
        self.submissions = []
        InlineExecutor.last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        self.submissions.append((fn, args, kwargs))
        fut = concurrent.futures.Future()
        try:
            fut.set_result(fn(*args, **kwargs))
        except Exception as exc:
            fut.set_exception(exc)
        return fut


class TestParallelExtraction(unittest.TestCase):
    def test_collect_pdfs_recurses_and_sorts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            nested = root / "SEG" / "financial_performance"
            nested.mkdir(parents=True)
            pdf_b = nested / "b.pdf"
            pdf_a = nested / "a.pdf"
            other = nested / "notes.txt"
            pdf_b.write_bytes(b"%PDF-1.4\n")
            pdf_a.write_bytes(b"%PDF-1.4\n")
            other.write_text("ignore", encoding="utf-8")

            pdfs = MOD.collect_pdfs(root)

        self.assertEqual(pdfs, [pdf_a.resolve(), pdf_b.resolve()])

    def test_run_pdf_extraction_uses_runtime_python_and_isolated_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdf_path = root / "financial-engine_v2" / "data" / "asx" / "docs" / "SEG" / "financial_performance" / "seg-report.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4\n")
            completed = MOD.subprocess.CompletedProcess(
                args=["placeholder"],
                returncode=0,
                stdout="ok\n",
                stderr="",
            )

            with mock.patch.object(MOD, "ROOT", root), mock.patch.object(
                MOD,
                "resolve_python",
                return_value="/tmp/docling-python",
            ), mock.patch.object(MOD.subprocess, "run", return_value=completed) as run_mock:
                result = MOD.run_pdf_extraction(pdf_path)

        self.assertEqual(result["returncode"], 0)
        cmd = run_mock.call_args.kwargs["args"] if "args" in run_mock.call_args.kwargs else run_mock.call_args.args[0]
        self.assertEqual(cmd[0], "/tmp/docling-python")
        self.assertEqual(cmd[1], str(root / "scripts" / "extract_financial_metrics.py"))
        self.assertEqual(cmd[2:4], ["--pdf", str(pdf_path.resolve())])
        self.assertIn("--out-json", cmd)
        self.assertIn("--out-sqlite", cmd)
        output_dir = Path(result["output_dir"])
        self.assertTrue(str(output_dir).startswith(str(root / "reports" / "parallel_extraction")))
        self.assertTrue(output_dir.name.startswith("seg-report"))

    def test_run_parallel_extraction_continues_after_worker_failures(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pdfs = [
                root / "one.pdf",
                root / "two.pdf",
                root / "three.pdf",
            ]
            for pdf in pdfs:
                pdf.write_bytes(b"%PDF-1.4\n")

            processed = []
            messages = []

            def fake_worker(pdf_path: Path):
                processed.append(Path(pdf_path).name)
                if Path(pdf_path).name == "two.pdf":
                    raise RuntimeError("boom")
                return {
                    "pdf_path": str(Path(pdf_path).resolve()),
                    "output_dir": str(root / "reports" / Path(pdf_path).stem),
                    "returncode": 0,
                    "stdout_tail": [],
                    "stderr_tail": [],
                }

            summary = MOD.run_parallel_extraction(
                pdfs,
                max_workers=3,
                worker_fn=fake_worker,
                executor_cls=InlineExecutor,
                printer=messages.append,
            )

        self.assertEqual(set(processed), {"one.pdf", "two.pdf", "three.pdf"})
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["succeeded"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["max_workers"], 3)
        self.assertIsNotNone(InlineExecutor.last_instance)
        self.assertEqual(InlineExecutor.last_instance.max_workers, 3)
        self.assertEqual(len(InlineExecutor.last_instance.submissions), 3)
        self.assertTrue(any("[worker] failed two.pdf" in msg for msg in messages))
        self.assertEqual(sum(1 for msg in messages if msg.startswith("[progress]")), 3)


if __name__ == "__main__":
    unittest.main()
