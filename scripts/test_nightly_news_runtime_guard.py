#!/usr/bin/env python3
"""Static regression tests for nightly news runtime guardrails."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "financial-engine_v2" / "scripts" / "nightly_news.sh"


class NightlyNewsRuntimeGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT_PATH.read_text(encoding="utf-8")

    def test_backend_venv_missing_fails_instead_of_succeeding_fetch_only(self) -> None:
        self.assertIn("failure_backend_venv_missing", self.script)
        self.assertIn("cannot run Qdrant sync or memo work", self.script)
        self.assertNotIn("skipped Qdrant sync and memo work", self.script)
        self.assertIsNotNone(
            re.search(r"failure_backend_venv_missing.*?exit 1", self.script, flags=re.S),
            "backend venv missing must make the nightly wrapper fail closed",
        )

    def test_qdrant_ready_is_checked_before_loader_sync(self) -> None:
        ensure_pos = self.script.index(
            '    ensure_qdrant_ready\n    python3 "${TENN_ROOT}/scripts/load_news_to_qdrant.py"'
        )
        loader_pos = self.script.index('python3 "${TENN_ROOT}/scripts/load_news_to_qdrant.py"')
        self.assertLess(ensure_pos, loader_pos)
        self.assertIn("--qdrant-url", self.script)
        self.assertIn('qdrant_sync.get("status") != "success"', self.script)
        self.assertIn('qdrant_diff.get("status") != "available"', self.script)
        self.assertIn('sqlite_fallback.get("status") != "success"', self.script)

    def test_qdrant_self_heal_is_limited_to_existing_container_start(self) -> None:
        self.assertIn('QDRANT_CONTAINER="${NIGHTLY_NEWS_QDRANT_CONTAINER:-fe_qdrant}"', self.script)
        self.assertIn('QDRANT_AUTO_START="${NIGHTLY_NEWS_QDRANT_AUTO_START:-1}"', self.script)
        self.assertIn('docker container inspect "${QDRANT_CONTAINER}"', self.script)
        self.assertIn('docker start "${QDRANT_CONTAINER}"', self.script)
        self.assertNotIn("docker run", self.script)
        self.assertNotIn("docker compose up", self.script)

    def test_status_json_records_qdrant_runtime_context(self) -> None:
        self.assertIn('"qdrant": {', self.script)
        self.assertIn('"url": env("NIGHTLY_NEWS_QDRANT_URL_EFFECTIVE")', self.script)
        self.assertIn('"container": env("NIGHTLY_NEWS_QDRANT_CONTAINER")', self.script)
        self.assertIn('"auto_start": env("NIGHTLY_NEWS_QDRANT_AUTO_START")', self.script)

    def test_memo_dispatch_uses_durable_memory_root_and_explicit_llm(self) -> None:
        self.assertIn("TENN_RESEARCH_MEMORY_ROOT", self.script)
        self.assertIn(
            "/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory",
            self.script,
        )
        self.assertIn(
            'MEMO_DIAGNOSTICS_PATH="${TENN_RESEARCH_MEMORY_ROOT}/news_memos.jsonl"',
            self.script,
        )
        self.assertNotIn(
            'MEMO_DIAGNOSTICS_PATH="${TENN_ROOT}/financial-engine_v2/data/reports/research_memory/news_memos.jsonl"',
            self.script,
        )
        self.assertIn("--memo-llm-url", self.script)
        self.assertIn("--memo-llm-model", self.script)
        self.assertIn("NEWS_MEMO_LLM_URL_EFFECTIVE", self.script)
        self.assertIn("NEWS_MEMO_LLM_MODEL_EFFECTIVE", self.script)

    def test_no_destructive_qdrant_operations_in_wrapper(self) -> None:
        destructive_patterns = [
            r"delete_collection",
            r"recreate_collection",
            r"docker\s+rm",
            r"docker\s+volume\s+rm",
            r"--cleanup-stale",
        ]
        for pattern in destructive_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.script))


if __name__ == "__main__":
    unittest.main()
