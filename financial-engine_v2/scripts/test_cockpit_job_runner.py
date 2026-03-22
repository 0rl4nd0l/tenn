#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cockpit.core.job_runner import JobRunner  # noqa: E402
from cockpit.core.types import JobRun  # noqa: E402


def _make_job(action_id: str = "test_action") -> JobRun:
    return JobRun(
        job_id="test-job-001",
        action_id=action_id,
        args={},
        started_at=datetime.now(timezone.utc),
        status="queued",
    )


class JobRunnerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.logs_dir = self.tmp / "logs"
        self.runner = JobRunner(repo_root=REPO_ROOT, logs_dir=self.logs_dir)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    # ------------------------------------------------------------------
    # 1. Successful command
    # ------------------------------------------------------------------
    async def test_successful_command_status_and_stdout(self) -> None:
        job = _make_job()
        result = await self.runner.run(
            job=job,
            command=["python3", "-c", "print('hello')"],
            timeout_seconds=10,
        )
        self.assertEqual(result.status, "success")
        self.assertEqual(result.exit_code, 0)
        self.assertIsNotNone(result.stdout_path)
        stdout_content = Path(result.stdout_path).read_text(encoding="utf-8", errors="replace")
        self.assertIn("hello", stdout_content)

    # ------------------------------------------------------------------
    # 2. Failed command — non-zero exit code
    # ------------------------------------------------------------------
    async def test_failed_command_status_and_exit_code(self) -> None:
        job = _make_job()
        result = await self.runner.run(
            job=job,
            command=["python3", "-c", "import sys; sys.exit(1)"],
            timeout_seconds=10,
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.exit_code, 1)

    # ------------------------------------------------------------------
    # 3. Timeout kills the process
    # ------------------------------------------------------------------
    async def test_timeout_kills_process_and_returns_failed(self) -> None:
        job = _make_job()
        start = time.monotonic()
        result = await self.runner.run(
            job=job,
            command=["python3", "-c", "import time; time.sleep(60)"],
            timeout_seconds=2,
        )
        elapsed = time.monotonic() - start
        # Should terminate well within 5 seconds (we gave it a 2s timeout)
        self.assertLess(elapsed, 5.0, msg=f"Timeout test took too long: {elapsed:.1f}s")
        self.assertEqual(result.status, "failed")
        # exit_code 124 is what job_runner uses for timeouts
        self.assertEqual(result.exit_code, 124)

    # ------------------------------------------------------------------
    # 4. cancel_active with no active job returns "none"
    # ------------------------------------------------------------------
    async def test_cancel_active_no_job_returns_none(self) -> None:
        result = await self.runner.cancel_active()
        self.assertEqual(result, "none")

    # ------------------------------------------------------------------
    # 5. on_output callback receives output lines
    # ------------------------------------------------------------------
    async def test_on_output_callback_receives_lines(self) -> None:
        received: list[str] = []

        def _capture(line: str) -> None:
            received.append(line)

        job = _make_job()
        await self.runner.run(
            job=job,
            command=["python3", "-c", "print('line-one'); print('line-two')"],
            timeout_seconds=10,
            on_output=_capture,
        )
        combined = "\n".join(received)
        self.assertIn("line-one", combined)
        self.assertIn("line-two", combined)


if __name__ == "__main__":
    unittest.main()
