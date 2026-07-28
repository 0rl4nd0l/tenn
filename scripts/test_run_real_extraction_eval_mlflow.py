import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_real_extraction_eval_mlflow.py"
spec = importlib.util.spec_from_file_location(
    "run_real_extraction_eval_mlflow", SCRIPT_PATH
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class _Run:
    info = SimpleNamespace(run_id="aggregate-run")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _Mlflow:
    def __init__(self):
        self.params = {}
        self.metrics = {}
        self.artifacts = []

    def start_run(self, *, run_name):
        return _Run()

    def log_param(self, key, value):
        self.params[key] = value

    def log_metric(self, key, value):
        self.metrics[key] = value

    def log_artifact(self, path, *, artifact_path):
        self.artifacts.append((path, artifact_path))

    def log_dict(self, payload, path):
        self.artifacts.append((payload, path))


class TestMlflowHoldoutConfidentiality(unittest.TestCase):
    def test_development_run_logs_only_aggregate_fields_and_validated_json(self):
        aggregate = {
            "corpus_version": "opaque-v1",
            "corpus_digest": "a" * 64,
            "document_count": 48,
            "partition_counts": {"diagnostic": 12, "holdout": 36},
            "bucket_counts": {
                "annual": 8,
                "4E": 8,
                "half-year": 8,
                "4D": 8,
                "quarterly": 8,
                "4C": 8,
            },
            "company_count": 12,
            "sector_count": 6,
            "scan_image_heavy_count": 6,
            "non_aud_count": 1,
            "issuer_size_counts": {"large": 24, "small": 24},
        }
        fake = _Mlflow()
        run = mod._log_development_aggregate(
            fake,
            aggregate,
            run_name="aggregate",
        )

        self.assertEqual(run.info.run_id, "aggregate-run")
        self.assertEqual(
            set(fake.params) | set(fake.metrics),
            set(mod.DevelopmentAggregateResult.ALLOWED_FIELDS),
        )
        logged = json.dumps(
            {
                "params": fake.params,
                "metrics": fake.metrics,
                "artifacts": fake.artifacts,
            }
        )
        for secret in (
            "document_id",
            "ticker",
            "expected",
            "actual",
            "trust_trigger",
        ):
            self.assertNotIn(secret, logged)
        self.assertEqual(
            fake.artifacts,
            [(aggregate, "eval/development_aggregate.json")],
        )


if __name__ == "__main__":
    unittest.main()
