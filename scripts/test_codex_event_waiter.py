from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from scripts import codex_event_waiter as waiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def snapshot(
    *,
    head_sha: str = "abc123",
    pr_state: str = "OPEN",
    merged: bool = False,
    rollup_state: str | None = "PENDING",
    contexts: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "head_sha": head_sha,
        "pr_state": pr_state,
        "merged": merged,
        "is_draft": True,
        "rollup_state": rollup_state,
        "contexts": contexts or [],
        "url": "https://github.example/pr/1",
    }


class GitHubWaitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.config = waiter.GitHubWaitConfig(
            repo="owner/repo",
            pr_number=1,
            expected_head_sha="abc123",
            poll_seconds=1.0,
            timeout_seconds=20.0,
        )

    def sequence_fetcher(self, values: list[object]):
        remaining = list(values)

        def fetcher(_repo: str, _number: int) -> dict[str, object]:
            value = remaining.pop(0) if len(remaining) > 1 else remaining[0]
            if isinstance(value, Exception):
                raise value
            return value  # type: ignore[return-value]

        return fetcher

    def wait(self, values: list[object]) -> dict[str, object]:
        return waiter.wait_for_github_pr(
            self.config,
            fetch_snapshot=self.sequence_fetcher(values),
            sleep=self.clock.sleep,
            monotonic=self.clock.monotonic,
        )

    def test_success_requires_two_identical_terminal_snapshots(self) -> None:
        success = snapshot(
            rollup_state="SUCCESS",
            contexts=[{"name": "tests", "state": "SUCCESS", "kind": "check_run"}],
        )
        result = self.wait([snapshot(), success, success])
        self.assertEqual(result["state"], "SUCCESS")
        self.assertEqual(result["observed"]["stable_terminal_snapshots"], 2)
        self.assertEqual(result["observed"]["poll_count"], 3)

    def test_head_change_fails_closed(self) -> None:
        result = self.wait([snapshot(head_sha="different")])
        self.assertEqual(result["state"], "STALE_TARGET")

    def test_failed_rollup_is_terminal(self) -> None:
        result = self.wait([snapshot(rollup_state="FAILURE")])
        self.assertEqual(result["state"], "FAILURE")

    def test_merged_elsewhere_is_success(self) -> None:
        result = self.wait([snapshot(pr_state="MERGED", merged=True, rollup_state=None)])
        self.assertEqual(result["state"], "SUCCESS")
        self.assertEqual(result["observed"]["outcome"], "merged")

    def test_closed_unmerged_is_cancelled(self) -> None:
        result = self.wait([snapshot(pr_state="CLOSED", rollup_state=None)])
        self.assertEqual(result["state"], "CANCELLED")

    def test_three_consecutive_api_errors_are_terminal(self) -> None:
        result = self.wait([RuntimeError("one"), RuntimeError("two"), RuntimeError("three")])
        self.assertEqual(result["state"], "ERROR")
        self.assertEqual(result["observed"]["consecutive_api_errors"], 3)
        self.assertNotIn("token", json.dumps(result).lower())

    def test_pending_rollup_times_out(self) -> None:
        config = waiter.GitHubWaitConfig(
            repo="owner/repo",
            pr_number=1,
            expected_head_sha="abc123",
            poll_seconds=0.5,
            timeout_seconds=1.0,
        )
        result = waiter.wait_for_github_pr(
            config,
            fetch_snapshot=lambda _repo, _number: snapshot(),
            sleep=self.clock.sleep,
            monotonic=self.clock.monotonic,
        )
        self.assertEqual(result["state"], "TIMEOUT")


class CommandWaitTests(unittest.TestCase):
    def test_redact_text_covers_real_github_pat_prefixes(self) -> None:
        classic = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        fine_grained = "github_pat_11AA0_example_token_value"

        redacted = waiter.redact_text(f"classic={classic} fine={fine_grained}")

        self.assertNotIn(classic, redacted)
        self.assertNotIn(fine_grained, redacted)
        self.assertEqual(redacted.count("[REDACTED]"), 2)

    def test_command_success_captures_bounded_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            result = waiter.run_command_wait(
                [sys.executable, "-c", "print('done')"],
                timeout_seconds=5.0,
                max_log_bytes=1024,
                output_path=result_path,
            )
            self.assertEqual(result["state"], "SUCCESS")
            self.assertEqual(result["observed"]["exit_code"], 0)
            log_path = Path(result["evidence"]["log_path"])
            self.assertEqual(log_path.read_text(encoding="utf-8").strip(), "done")

    def test_command_arguments_are_not_interpreted_by_a_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "should-not-exist"
            dangerous = f"; touch {sentinel}"
            result = waiter.run_command_wait(
                [sys.executable, "-c", "import sys; print(sys.argv[1])", dangerous],
                timeout_seconds=5.0,
                max_log_bytes=1024,
                output_path=Path(directory) / "result.json",
            )
            self.assertEqual(result["state"], "SUCCESS")
            self.assertFalse(sentinel.exists())

    def test_command_failure_preserves_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = waiter.run_command_wait(
                [sys.executable, "-c", "raise SystemExit(7)"],
                timeout_seconds=5.0,
                max_log_bytes=1024,
                output_path=Path(directory) / "result.json",
            )
            self.assertEqual(result["state"], "FAILURE")
            self.assertEqual(result["observed"]["exit_code"], 7)

    def test_command_log_is_bounded_and_redacts_common_secret_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = waiter.run_command_wait(
                [
                    sys.executable,
                    "-c",
                    "print('A' * 2000); print('token=do-not-log-this')",
                ],
                timeout_seconds=5.0,
                max_log_bytes=128,
                output_path=Path(directory) / "result.json",
            )
            log_text = Path(result["evidence"]["log_path"]).read_text(encoding="utf-8")
            self.assertLessEqual(len(log_text.encode("utf-8")), 128)
            self.assertNotIn("do-not-log-this", log_text)
            self.assertIn("token=[REDACTED]", log_text)

    def test_redaction_expansion_still_respects_log_byte_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = waiter.run_command_wait(
                [sys.executable, "-c", "print('token=x')"],
                timeout_seconds=5.0,
                max_log_bytes=8,
                output_path=Path(directory) / "result.json",
            )
            log_text = Path(result["evidence"]["log_path"]).read_text(encoding="utf-8")
            self.assertLessEqual(len(log_text.encode("utf-8")), 8)
            self.assertNotIn("x", log_text)

    def test_truncated_log_drops_partial_line_before_redaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = waiter.run_command_wait(
                [
                    sys.executable,
                    "-c",
                    "print('token=' + 'A' * 200); print('safe-tail')",
                ],
                timeout_seconds=5.0,
                max_log_bytes=64,
                output_path=Path(directory) / "result.json",
            )
            log_text = Path(result["evidence"]["log_path"]).read_text(encoding="utf-8")
            self.assertLessEqual(len(log_text.encode("utf-8")), 64)
            self.assertNotIn("AAAAAAAA", log_text)
            self.assertIn("safe-tail", log_text)

    def test_command_timeout_terminates_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = waiter.run_command_wait(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout_seconds=0.1,
                max_log_bytes=1024,
                output_path=Path(directory) / "result.json",
            )
            self.assertEqual(result["state"], "TIMEOUT")
            self.assertTrue(result["observed"]["termination_attempted"])

    @unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-specific")
    def test_command_timeout_kills_sigterm_resistant_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            group_pid_path = Path(directory) / "group.pid"
            child_pid_path = Path(directory) / "child.pid"
            heartbeat_path = Path(directory) / "heartbeat"
            child_code = "\n".join(
                [
                    "import os",
                    "import signal",
                    "import time",
                    "signal.signal(signal.SIGTERM, signal.SIG_IGN)",
                    f"open({str(child_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    "while True:",
                    f"    with open({str(heartbeat_path)!r}, 'a', encoding='utf-8') as handle:",
                    "        handle.write('x')",
                    "    time.sleep(0.02)",
                ]
            )
            leader_code = "\n".join(
                [
                    "import os",
                    "import subprocess",
                    "import sys",
                    "import time",
                    f"open({str(group_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    f"subprocess.Popen([sys.executable, '-c', {child_code!r}])",
                    "time.sleep(30)",
                ]
            )

            try:
                result = waiter.run_command_wait(
                    [sys.executable, "-c", leader_code],
                    timeout_seconds=0.2,
                    max_log_bytes=1024,
                    output_path=Path(directory) / "result.json",
                )
                self.assertEqual(result["state"], "TIMEOUT")
                self.assertTrue(group_pid_path.exists())
                self.assertTrue(child_pid_path.exists())
                self.assertTrue(heartbeat_path.exists())
                size_after_wait = heartbeat_path.stat().st_size
                time.sleep(0.15)
                self.assertEqual(heartbeat_path.stat().st_size, size_after_wait)
            finally:
                if group_pid_path.exists():
                    try:
                        os.killpg(int(group_pid_path.read_text(encoding="utf-8")), signal.SIGKILL)
                    except ProcessLookupError:
                        pass


class OutputAndCliTests(unittest.TestCase):
    def test_write_terminal_result_is_atomic_and_stdout_is_one_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "result.json"
            payload = waiter.build_terminal_result(
                kind="command",
                state="SUCCESS",
                started_at="2026-07-10T00:00:00Z",
                target={"executable": "true"},
                observed={"exit_code": 0},
                summary="command completed",
            )
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                waiter.write_and_emit(payload, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)
            self.assertEqual(len(stream.getvalue().splitlines()), 1)
            self.assertFalse(any(output.parent.glob("*.tmp")))

    def test_cli_command_emits_one_line_and_writes_matching_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(waiter.__file__).resolve()),
                    "command",
                    "--output",
                    str(output),
                    "--",
                    sys.executable,
                    "-c",
                    "print('ok')",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(len(completed.stdout.splitlines()), 1)
            self.assertEqual(json.loads(completed.stdout), json.loads(output.read_text(encoding="utf-8")))

    @unittest.skipUnless(os.name == "posix", "process-group interruption is POSIX-specific")
    def test_cli_interrupt_terminates_child_and_emits_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            pid_path = Path(directory) / "child.pid"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(waiter.__file__).resolve()),
                    "command",
                    "--output",
                    str(output),
                    "--",
                    sys.executable,
                    "-c",
                    (
                        "import os,time; "
                        f"open({str(pid_path)!r}, 'w').write(str(os.getpid())); "
                        "time.sleep(30)"
                    ),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            deadline = time.monotonic() + 5
            while not pid_path.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pid_path.exists(), "child PID was not reported")
            child_pid = int(pid_path.read_text(encoding="utf-8"))
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 1, stderr)
            self.assertEqual(json.loads(stdout)["state"], "CANCELLED")
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)


if __name__ == "__main__":
    unittest.main()
