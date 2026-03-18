import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class TestCeleryTaskRegistrationSmoke(unittest.TestCase):
    def test_expected_tasks_registered(self):
        from app.celery_app import celery
        import app.tasks.commentary_tasks  # noqa: F401
        import app.worker_tasks  # noqa: F401

        tasks = set(celery.tasks.keys())
        self.assertIn("backfill_ticker", tasks)
        self.assertIn("download_pdf", tasks)
        self.assertIn("process_document", tasks)
        self.assertIn("llm_generate_json", tasks)
        self.assertIn("llm_embed_texts", tasks)
        self.assertIn("extract_commentary_memo_task", tasks)

    def test_specialized_queues_configured(self):
        from app.celery_app import celery

        queue_names = {queue.name for queue in celery.conf.task_queues}
        self.assertEqual(
            queue_names,
            {"ingest", "embed", "score", "llm_gpu", "llm_cpu"},
        )


if __name__ == "__main__":
    unittest.main()
