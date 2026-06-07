import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "financial-engine_v2" / "scripts" / "nightly_news.sh"


def _latest_json(log_dir: Path, suffix: str) -> dict:
    matches = sorted(log_dir.glob(f"nightly_news_*.{suffix}.json"))
    if not matches:
        raise AssertionError(f"no nightly_news_*.{suffix}.json under {log_dir}")
    return json.loads(matches[-1].read_text(encoding="utf-8"))


def _write_eodhd_capture_fixture(captures: Path, published_at: str) -> None:
    captures.mkdir(parents=True, exist_ok=True)
    (captures / "market_news_sample.json").write_text(
        json.dumps(
            [
                {
                    "id": "mk1",
                    "title": "ASX:BHP posts production update",
                    "link": "https://example.com/market/bhp",
                    "date": published_at,
                    "source": "Example AU",
                    "description": "BHP Group released an ASX production update.",
                    "content": "ASX:BHP reported a production update with operational details.",
                }
            ]
        ),
        encoding="utf-8",
    )
    (captures / "symbol_BHP_sample.json").write_text(
        json.dumps(
            [
                {
                    "id": "sym1",
                    "title": "BHP.AX guidance reaffirmed",
                    "link": "https://example.com/symbol/bhp",
                    "date": published_at,
                    "source": "Example AU",
                    "description": "BHP guidance remains unchanged.",
                    "content": "BHP.AX guidance remains unchanged after the update.",
                }
            ]
        ),
        encoding="utf-8",
    )


class NightlyNewsWrapperTests(unittest.TestCase):
    def _base_env(self, tmp: Path, *, providers: str = "eodhd") -> dict[str, str]:
        tickers = tmp / "tickers.txt"
        identity = tmp / "ticker_identity_map.json"
        captures = tmp / "captures"
        logs = tmp / "logs"
        artifacts = tmp / "qual_context"
        captures.mkdir(parents=True, exist_ok=True)
        tickers.write_text("BHP\n", encoding="utf-8")
        identity.write_text(
            json.dumps({"BHP": {"canonical_names": ["BHP Group"], "aliases": ["BHP"]}}),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update(
            {
                "NIGHTLY_NEWS_PYTHON": sys.executable,
                "NIGHTLY_NEWS_LOG_DIR": str(logs),
                "TENN_NEWS_ARTIFACT_ROOT": str(artifacts),
                "NEWS_TICKERS_FILE": str(tickers),
                "NEWS_IDENTITY_MAP_PATH": str(identity),
                "NIGHTLY_NEWS_PROVIDERS": providers,
                "NEWS_EODHD_CAPTURE_DIR": str(captures),
                "NEWS_MAX_TICKERS": "1",
                "NIGHTLY_NEWS_MIN_FETCHED": "1",
                "NIGHTLY_NEWS_MIN_UPSERTED": "1",
                "NIGHTLY_NEWS_MIN_CHUNKS": "1",
                "NIGHTLY_NEWS_MAX_ERRORS": "0",
            }
        )
        return env

    def test_dry_run_writes_status_without_fetching(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            env["NIGHTLY_NEWS_DRY_RUN"] = "1"
            proc = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)

            status = _latest_json(tmp / "logs", "status")
            health = _latest_json(tmp / "logs", "health")
            self.assertEqual(status["status"], "success")
            self.assertTrue(status["dry_run"])
            self.assertEqual(status["phases"]["fetch"], "skipped_dry_run")
            self.assertEqual(status["phases"]["build"], "skipped_dry_run")
            self.assertEqual(health["status"], "success")
            self.assertTrue(health["dry_run"])
            self.assertFalse((tmp / "qual_context" / "news_articles.sqlite").exists())

    def test_default_dry_run_uses_newspaper4k(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            env.pop("NIGHTLY_NEWS_PROVIDERS", None)
            env["NIGHTLY_NEWS_DRY_RUN"] = "1"
            proc = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)

            status = _latest_json(tmp / "logs", "status")
            self.assertEqual(status["status"], "success")
            self.assertEqual(status["config"]["providers"], "newspaper4k")

    def test_capture_backed_run_builds_temp_sqlite_and_health(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            captures = Path(env["NEWS_EODHD_CAPTURE_DIR"])
            now = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            _write_eodhd_capture_fixture(captures, now)

            proc = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)

            status = _latest_json(tmp / "logs", "status")
            health = _latest_json(tmp / "logs", "health")
            fetch = _latest_json(tmp / "logs", "fetch")
            chunks = _latest_json(tmp / "logs", "chunks")
            self.assertEqual(status["status"], "success")
            self.assertFalse(status["dry_run"])
            self.assertEqual(status["phases"]["fetch"], "success")
            self.assertEqual(status["phases"]["build"], "success")
            self.assertEqual(status["phases"]["health"], "success")
            self.assertEqual(health["status"], "success")
            self.assertGreaterEqual(int(health["totals"]["fetched"]), 1)
            self.assertGreaterEqual(int(health["totals"]["inserted"]), 1)
            self.assertEqual(int(health["totals"]["errors"]), 0)
            self.assertGreaterEqual(int(health["totals"]["chunks_written"]), 1)
            self.assertTrue(health["context"]["changed"])
            self.assertGreaterEqual(int(health["context"]["after"]["recent_news_chunks"]), 1)
            self.assertEqual(fetch["providers"], ["eodhd"])
            self.assertGreaterEqual(len(fetch["runs"]), 1)
            self.assertGreaterEqual(int(chunks["stats"]["chunks_written"]), 1)
            self.assertTrue((tmp / "qual_context" / "news_articles.sqlite").exists())
            self.assertTrue((tmp / "qual_context" / "news.sqlite").exists())

    def test_duplicate_fetch_zero_upsert_fails_even_with_existing_context(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            captures = Path(env["NEWS_EODHD_CAPTURE_DIR"])
            now = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            _write_eodhd_capture_fixture(captures, now)

            first = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(first.returncode, 0, first.stdout)

            env = dict(env)
            env["NIGHTLY_NEWS_LOG_DIR"] = str(tmp / "logs_second")
            second = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(second.returncode, 0, second.stdout)

            status = _latest_json(tmp / "logs_second", "status")
            health = _latest_json(tmp / "logs_second", "health")
            self.assertEqual(status["status"], "failure")
            self.assertEqual(status["failed_phase"], "health")
            self.assertEqual(health["status"], "failure")
            self.assertGreaterEqual(int(health["totals"]["fetched"]), 1)
            self.assertEqual(int(health["totals"]["inserted"]), 0)
            self.assertGreaterEqual(int(health["totals"]["deduped"]), 1)
            self.assertGreaterEqual(int(health["totals"]["chunks_written"]), 1)
            self.assertTrue(any("inserted/upserted 0 below minimum 1" in item for item in health["problems"]))
            self.assertIn("context", health)

    def test_stale_context_chunks_outside_current_window_fail_health(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            captures = Path(env["NEWS_EODHD_CAPTURE_DIR"])
            old = (datetime.now(tz=timezone.utc) - timedelta(days=10)).replace(microsecond=0).isoformat().replace(
                "+00:00",
                "Z",
            )
            _write_eodhd_capture_fixture(captures, old)

            wide_env = dict(env)
            wide_env["NIGHTLY_NEWS_SINCE_HOURS"] = "720"
            first = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=wide_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertEqual(first.returncode, 0, first.stdout)

            narrow_env = dict(env)
            narrow_env["NIGHTLY_NEWS_LOG_DIR"] = str(tmp / "logs_narrow")
            narrow_env["NIGHTLY_NEWS_SINCE_HOURS"] = "1"
            second = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=narrow_env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(second.returncode, 0, second.stdout)

            health = _latest_json(tmp / "logs_narrow", "health")
            self.assertEqual(health["status"], "failure")
            self.assertEqual(int(health["totals"]["chunks_written"]), 2)
            self.assertEqual(int(health["context"]["after"]["recent_news_chunks"]), 0)
            self.assertTrue(any("context recent news chunks 0 below minimum 1" in item for item in health["problems"]))

    def test_zero_fetch_fails_health(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            env = self._base_env(tmp)
            proc = subprocess.run(
                [str(WRAPPER)],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)

            status = _latest_json(tmp / "logs", "status")
            health = _latest_json(tmp / "logs", "health")
            self.assertEqual(status["status"], "failure")
            self.assertEqual(status["failed_phase"], "health")
            self.assertEqual(health["status"], "failure")
            self.assertEqual(int(health["totals"]["fetched"]), 0)
            self.assertGreaterEqual(int(health["totals"]["errors"]), 1)
            self.assertTrue(any("fetched 0 below minimum" in item for item in health["problems"]))
            self.assertTrue(any("chunks_written 0 below minimum" in item for item in health["problems"]))


if __name__ == "__main__":
    unittest.main()
