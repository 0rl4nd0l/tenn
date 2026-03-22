import importlib
import os
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

    def test_celery_urls_follow_normalized_settings_even_with_env_overrides(self):
        original_env = dict(os.environ)
        try:
            os.environ["CELERY_BROKER_URL"] = "redis://redis:6379/0"
            os.environ["CELERY_RESULT_BACKEND"] = "redis://redis:6379/1"
            os.environ["TENN_HOST_NETWORK"] = "true"
            os.environ["DATABASE_URL"] = "sqlite:////tmp/celery_smoke.db"
            os.environ["LLAMACPP_URL"] = "http://127.0.0.1:8001"
            os.environ["OLLAMA_URL"] = "http://127.0.0.1:11434"

            import app.core.config as config_module
            import app.celery_app as celery_module

            config_module = importlib.reload(config_module)
            celery_module = importlib.reload(celery_module)

            self.assertEqual(celery_module.celery.conf.broker_url, config_module.settings.celery_broker_url)
            self.assertEqual(celery_module.celery.conf.result_backend, config_module.settings.celery_result_backend)
            self.assertEqual(config_module.settings.celery_broker_url, "redis://127.0.0.1:6379/0")
            self.assertEqual(config_module.settings.celery_result_backend, "redis://127.0.0.1:6379/1")
        finally:
            os.environ.clear()
            os.environ.update(original_env)


if __name__ == "__main__":
    unittest.main()
