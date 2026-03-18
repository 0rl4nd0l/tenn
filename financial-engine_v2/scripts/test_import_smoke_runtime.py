import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class TestImportSmokeRuntime(unittest.TestCase):
    def test_backend_main_import(self):
        import app.main as main  # noqa: F401

    def test_celery_app_import(self):
        from app.celery_app import celery

        self.assertIsNotNone(celery)

    def test_pipeline_service_import(self):
        from app.services.pipeline_service import PipelineJobSpec, run_pipeline_sync

        self.assertIsNotNone(PipelineJobSpec)
        self.assertTrue(callable(run_pipeline_sync))


if __name__ == "__main__":
    unittest.main()
