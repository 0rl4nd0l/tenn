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

    def test_redact_text_preserves_quoted_json_shape(self) -> None:
        secret = "do-not-log-this"
        payload = '{"api_key":"' + secret + '","password":"also-secret"}'

        redacted = waiter.redact_text(payload)

        self.assertNotIn(secret, redacted)
        self.assertNotIn("also-secret", redacted)
        self.assertEqual(
            json.loads(redacted),
            {"api_key": "[REDACTED]", "password": "[REDACTED]"},
        )

    def test_redact_text_preserves_quoted_json_bearer_shape(self) -> None:
        cases = [
            (
                '{"Authorization":"Bearer generic-secret-123"}',
                {"Authorization": "Bearer [REDACTED]"},
            ),
            (
                '{"aUtHoRiZaTiOn" : "bEaReR Mixed-Secret_456"}',
                {"aUtHoRiZaTiOn": "bEaReR [REDACTED]"},
            ),
        ]

        for payload, expected in cases:
            with self.subTest(payload=payload):
                redacted = waiter.redact_text(payload)
                self.assertNotIn("secret", redacted.lower())
                self.assertEqual(json.loads(redacted), expected)

    def test_redact_text_handles_single_quoted_bearer_assignment(self) -> None:
        redacted = waiter.redact_text(
            "'authorization'='Bearer generic-secret-123'"
        )

        self.assertEqual(redacted, "'authorization'='Bearer [REDACTED]'")

    def test_redact_text_preserves_escaped_json_bearer_shape(self) -> None:
        payload = r'rpc payload="{\"Authorization\":\"Bearer escaped-secret-123\"}"'

        redacted = waiter.redact_text(payload)

        self.assertNotIn("escaped-secret-123", redacted)
        self.assertEqual(
            redacted,
            r'rpc payload="{\"Authorization\":\"Bearer [REDACTED]\"}"',
        )

    def test_redact_text_handles_json_encoded_json_bearer_value(self) -> None:
        payload = json.dumps(
            {
                "payload": json.dumps(
                    {"Authorization": "Bearer nested-secret-456"}
                )
            }
        )

        redacted = waiter.redact_text(payload)

        self.assertNotIn("nested-secret-456", redacted)
        decoded = json.loads(redacted)
        self.assertEqual(
            json.loads(decoded["payload"]),
            {"Authorization": "Bearer [REDACTED]"},
        )

    def test_redact_text_handles_escaped_quote_inside_json_bearer_value(self) -> None:
        payload = json.dumps(
            {
                "payload": json.dumps(
                    {"Authorization": 'Bearer secret"tail'}
                )
            }
        )

        redacted = waiter.redact_text(payload)

        self.assertNotIn("secret", redacted.lower())
        self.assertNotIn("tail", redacted.lower())
        decoded = json.loads(redacted)
        self.assertEqual(
            json.loads(decoded["payload"]),
            {"Authorization": "Bearer [REDACTED]"},
        )

    def test_redact_text_handles_multiple_json_serialization_layers(self) -> None:
        for depth in (2, 3):
            with self.subTest(depth=depth):
                payload: object = {"Authorization": "Bearer deep-secret-789"}
                for _ in range(depth):
                    payload = json.dumps({"payload": payload})

                redacted = waiter.redact_text(str(payload))

                self.assertNotIn("deep-secret-789", redacted)
                decoded: object = json.loads(redacted)
                for _ in range(depth - 1):
                    self.assertIsInstance(decoded, dict)
                    decoded = json.loads(decoded["payload"])
                self.assertEqual(
                    decoded,
                    {"payload": {"Authorization": "Bearer [REDACTED]"}},
                )

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


class ServiceWaitTests(unittest.TestCase):
    def assert_not_ready(self, path: Path) -> None:
        self.assertTrue(path.exists())
        self.assertNotEqual(
            json.loads(path.read_text(encoding="utf-8"))["state"],
            "READY",
        )

    def wait_for_ready(
        self,
        path: Path,
        process: subprocess.Popen[str],
        *,
        timeout_seconds: float = 3,
    ) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        while process.poll() is None and time.monotonic() < deadline:
            if path.exists():
                payload = json.loads(path.read_text(encoding="utf-8"))
                if payload.get("state") == "READY":
                    return payload
            time.sleep(0.02)
        self.fail("service did not emit READY before exiting or timing out")

    @unittest.skipUnless(os.name == "posix", "attached process supervision is POSIX-specific")
    def test_service_ready_record_is_written_while_process_remains_alive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service_pid_path = root / "service pid.txt"
            ready_path = root / "service ready.json"
            result_path = root / "service terminal.json"
            service_code = "\n".join(
                [
                    "import os",
                    "import time",
                    f"open({str(service_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    "while True:",
                    "    time.sleep(0.05)",
                ]
            )
            readiness_code = "\n".join(
                [
                    "import os",
                    "from pathlib import Path",
                    f"path = Path({str(service_pid_path)!r})",
                    "if not path.exists():",
                    "    raise SystemExit(1)",
                    "os.kill(int(path.read_text(encoding='utf-8')), 0)",
                ]
            )
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(waiter.__file__).resolve()),
                    "service",
                    "--output",
                    str(result_path),
                    "--ready-output",
                    str(ready_path),
                    "--readiness-command-json",
                    json.dumps([sys.executable, "-c", readiness_code]),
                    "--readiness-timeout-seconds",
                    "2",
                    "--poll-seconds",
                    "0.02",
                    "--",
                    sys.executable,
                    "-c",
                    service_code,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                ready = self.wait_for_ready(ready_path, process)
                service_pid = int(service_pid_path.read_text(encoding="utf-8"))
                self.assertEqual(ready["state"], "READY")
                self.assertEqual(ready["observed"]["service_pid"], service_pid)
                os.kill(service_pid, 0)

                process.send_signal(signal.SIGINT)
                process.communicate(timeout=5)

                terminal = json.loads(result_path.read_text(encoding="utf-8"))
                self.assertEqual(terminal["state"], "CANCELLED")
                self.assertTrue(terminal["observed"]["ready_observed"])
                with self.assertRaises(ProcessLookupError):
                    os.kill(service_pid, 0)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5)

    @unittest.skipUnless(os.name == "posix", "attached process supervision is POSIX-specific")
    def test_service_cli_preserves_exact_cockpit_start_new_argv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "fake bin"
            fake_bin.mkdir()
            argv_path = root / "cockpit argv.json"
            service_pid_path = root / "cockpit pid.txt"
            ready_path = root / "ready.json"
            result_path = root / "terminal.json"
            cockpit_path = fake_bin / "cockpit"
            cockpit_path.write_text(
                f"#!{sys.executable}\n"
                "import json\n"
                "import os\n"
                "import sys\n"
                "import time\n"
                f"open({str(argv_path)!r}, 'w', encoding='utf-8').write(json.dumps(sys.argv[1:]))\n"
                f"open({str(service_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))\n"
                "while True:\n"
                "    time.sleep(0.05)\n",
                encoding="utf-8",
            )
            cockpit_path.chmod(0o755)
            readiness_code = "\n".join(
                [
                    "import json",
                    "import os",
                    "from pathlib import Path",
                    f"argv_path = Path({str(argv_path)!r})",
                    f"pid_path = Path({str(service_pid_path)!r})",
                    "if not argv_path.exists() or not pid_path.exists():",
                    "    raise SystemExit(1)",
                    "os.kill(int(pid_path.read_text(encoding='utf-8')), 0)",
                    "raise SystemExit(0 if json.loads(argv_path.read_text(encoding='utf-8')) == ['start', 'new'] else 1)",
                ]
            )
            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(waiter.__file__).resolve()),
                    "service",
                    "--output",
                    str(result_path),
                    "--ready-output",
                    str(ready_path),
                    "--readiness-command-json",
                    json.dumps([sys.executable, "-c", readiness_code]),
                    "--readiness-timeout-seconds",
                    "2",
                    "--poll-seconds",
                    "0.02",
                    "--",
                    "cockpit",
                    "start",
                    "new",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                ready = self.wait_for_ready(ready_path, process)
                self.assertEqual(ready["target"]["executable"], "cockpit")
                self.assertEqual(ready["target"]["arg_count"], 3)
                self.assertEqual(
                    json.loads(argv_path.read_text(encoding="utf-8")),
                    ["start", "new"],
                )

                process.send_signal(signal.SIGINT)
                process.communicate(timeout=5)
                terminal = json.loads(result_path.read_text(encoding="utf-8"))
                self.assertEqual(terminal["state"], "CANCELLED")
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=5)

    @unittest.skipUnless(os.name == "posix", "attached signal supervision is POSIX-specific")
    def test_service_cli_signals_clean_up_process_and_write_terminal(self) -> None:
        supervised_signals = [signal.SIGTERM]
        if hasattr(signal, "SIGHUP"):
            supervised_signals.append(signal.SIGHUP)

        for supervised_signal in supervised_signals:
            with self.subTest(signal=supervised_signal), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                service_pid_path = root / "service.pid"
                ready_path = root / "ready.json"
                result_path = root / "terminal.json"
                service_code = "\n".join(
                    [
                        "import os",
                        "import time",
                        f"open({str(service_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                        "time.sleep(30)",
                    ]
                )
                readiness_code = "\n".join(
                    [
                        "from pathlib import Path",
                        f"raise SystemExit(0 if Path({str(service_pid_path)!r}).exists() else 1)",
                    ]
                )
                process = subprocess.Popen(
                    [
                        sys.executable,
                        str(Path(waiter.__file__).resolve()),
                        "service",
                        "--output",
                        str(result_path),
                        "--ready-output",
                        str(ready_path),
                        "--readiness-command-json",
                        json.dumps([sys.executable, "-c", readiness_code]),
                        "--readiness-timeout-seconds",
                        "2",
                        "--poll-seconds",
                        "0.02",
                        "--",
                        sys.executable,
                        "-c",
                        service_code,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                try:
                    self.wait_for_ready(ready_path, process)
                    service_pid = int(service_pid_path.read_text(encoding="utf-8"))
                    process.send_signal(supervised_signal)
                    process.communicate(timeout=5)

                    terminal = json.loads(result_path.read_text(encoding="utf-8"))
                    self.assertEqual(terminal["state"], "CANCELLED")
                    self.assertIn(
                        signal.Signals(supervised_signal).name,
                        terminal["summary"],
                    )
                    with self.assertRaises(ProcessLookupError):
                        os.kill(service_pid, 0)
                finally:
                    if process.poll() is None:
                        process.kill()
                    process.communicate(timeout=5)

    def test_service_exiting_before_readiness_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = waiter.run_service_wait(
                [sys.executable, "-c", "raise SystemExit(7)"],
                [sys.executable, "-c", "raise SystemExit(1)"],
                readiness_timeout_seconds=2,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=root / "ready.json",
            )

            self.assertEqual(result["state"], "FAILURE")
            self.assertEqual(result["observed"]["exit_code"], 7)
            self.assertFalse(result["observed"]["ready_observed"])
            self.assert_not_ready(root / "ready.json")

    @unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-specific")
    def test_service_wrapper_exit_cleans_up_live_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child_pid_path = root / "child.pid"
            child_code = "\n".join(
                [
                    "import os",
                    "import time",
                    f"open({str(child_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    "time.sleep(30)",
                ]
            )
            wrapper_code = "\n".join(
                [
                    "import subprocess",
                    "import sys",
                    "import time",
                    "from pathlib import Path",
                    f"subprocess.Popen([sys.executable, '-c', {child_code!r}])",
                    f"path = Path({str(child_pid_path)!r})",
                    "while not path.exists():",
                    "    time.sleep(0.01)",
                ]
            )
            result = waiter.run_service_wait(
                [sys.executable, "-c", wrapper_code],
                [sys.executable, "-c", "raise SystemExit(1)"],
                readiness_timeout_seconds=2,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=root / "ready.json",
            )

            self.assertEqual(result["state"], "FAILURE")
            self.assertTrue(result["observed"]["termination_attempted"])
            child_pid = int(child_pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)

    def test_readiness_probe_exit_cleans_up_live_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            probe_child_pid_path = root / "probe-child.pid"
            probe_child_code = "\n".join(
                [
                    "import os",
                    "import time",
                    f"open({str(probe_child_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    "time.sleep(30)",
                ]
            )
            probe_wrapper_code = "\n".join(
                [
                    "import subprocess",
                    "import sys",
                    "import time",
                    "from pathlib import Path",
                    f"subprocess.Popen([sys.executable, '-c', {probe_child_code!r}])",
                    f"path = Path({str(probe_child_pid_path)!r})",
                    "while not path.exists():",
                    "    time.sleep(0.01)",
                ]
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = waiter.run_service_wait(
                    [sys.executable, "-c", "import time; time.sleep(0.2)"],
                    [sys.executable, "-c", probe_wrapper_code],
                    readiness_timeout_seconds=2,
                    poll_seconds=0.02,
                    max_log_bytes=1024,
                    output_path=root / "terminal.json",
                    ready_output_path=root / "ready.json",
                )

            self.assertTrue(result["observed"]["ready_observed"])
            probe_child_pid = int(probe_child_pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(probe_child_pid, 0)

    def test_service_readiness_timeout_terminates_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service_pid_path = root / "service.pid"
            service_code = "\n".join(
                [
                    "import os",
                    "import time",
                    f"open({str(service_pid_path)!r}, 'w', encoding='utf-8').write(str(os.getpid()))",
                    "time.sleep(30)",
                ]
            )
            result = waiter.run_service_wait(
                [sys.executable, "-c", service_code],
                [sys.executable, "-c", "raise SystemExit(1)"],
                readiness_timeout_seconds=0.15,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=root / "ready.json",
            )

            self.assertEqual(result["state"], "TIMEOUT")
            self.assertTrue(result["observed"]["termination_attempted"])
            service_pid = int(service_pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(service_pid, 0)

    def test_service_and_readiness_arguments_preserve_spaces_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = "value with spaces; touch should-not-run"
            observed_path = root / "observed value.txt"
            ready_path = root / "ready result.json"
            service_code = "\n".join(
                [
                    "import sys",
                    "import time",
                    f"open({str(observed_path)!r}, 'w', encoding='utf-8').write(sys.argv[1])",
                    "time.sleep(0.2)",
                ]
            )
            readiness_code = (
                "import sys\n"
                "from pathlib import Path\n"
                "path = Path(sys.argv[1])\n"
                "expected = sys.argv[2]\n"
                "raise SystemExit(0 if path.exists() and "
                "path.read_text(encoding='utf-8') == expected else 1)"
            )
            with contextlib.redirect_stdout(io.StringIO()):
                result = waiter.run_service_wait(
                    [sys.executable, "-c", service_code, value],
                    [sys.executable, "-c", readiness_code, str(observed_path), value],
                    readiness_timeout_seconds=2,
                    poll_seconds=0.02,
                    max_log_bytes=1024,
                    output_path=root / "terminal result.json",
                    ready_output_path=ready_path,
                )

            self.assertTrue(ready_path.exists())
            self.assertEqual(observed_path.read_text(encoding="utf-8"), value)
            self.assertFalse((root / "should-not-run").exists())
            self.assertEqual(result["state"], "FAILURE")
            self.assertTrue(result["observed"]["ready_observed"])

    def test_service_missing_readiness_executable_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = waiter.run_service_wait(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                [str(root / "missing readiness executable")],
                readiness_timeout_seconds=2,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=root / "ready.json",
            )

            self.assertEqual(result["state"], "ERROR")
            self.assertTrue(result["observed"]["termination_attempted"])
            self.assert_not_ready(root / "ready.json")

    def test_service_missing_executable_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = waiter.run_service_wait(
                [str(root / "missing service executable")],
                [sys.executable, "-c", "raise SystemExit(0)"],
                readiness_timeout_seconds=2,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=root / "ready.json",
            )

            self.assertEqual(result["state"], "ERROR")
            self.assertIsNone(result["observed"]["service_pid"])
            self.assert_not_ready(root / "ready.json")

    def test_parse_argv_json_rejects_non_string_or_empty_argv(self) -> None:
        for value in ("{}", "[]", '[""]', '["python3", 1]'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                waiter.parse_argv_json(value, option="--readiness-command-json")

    def test_service_artifact_paths_must_be_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_path = root / "terminal.json"
            for ready_path in (output_path, Path(f"{output_path}.log")):
                with self.subTest(ready_path=ready_path), self.assertRaises(ValueError):
                    waiter.run_service_wait(
                        [sys.executable, "-c", "raise SystemExit(0)"],
                        [sys.executable, "-c", "raise SystemExit(0)"],
                        readiness_timeout_seconds=2,
                        poll_seconds=0.02,
                        max_log_bytes=1024,
                        output_path=output_path,
                        ready_output_path=ready_path,
                    )

    def test_service_replaces_stale_ready_before_startup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready_path = root / "ready.json"
            ready_path.write_text(
                '{"state":"READY","wait_id":"stale"}\n',
                encoding="utf-8",
            )
            result = waiter.run_service_wait(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                [sys.executable, "-c", "raise SystemExit(1)"],
                readiness_timeout_seconds=0.1,
                poll_seconds=0.02,
                max_log_bytes=1024,
                output_path=root / "terminal.json",
                ready_output_path=ready_path,
            )

            lifecycle = json.loads(ready_path.read_text(encoding="utf-8"))
            self.assertEqual(lifecycle["state"], "STARTING")
            self.assertEqual(lifecycle["wait_id"], result["wait_id"])
            self.assertNotEqual(lifecycle["wait_id"], "stale")

    def test_service_rejects_non_finite_timing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for readiness_timeout, poll_seconds in (
                (float("nan"), 1.0),
                (float("inf"), 1.0),
                (1.0, float("nan")),
                (1.0, float("inf")),
            ):
                with (
                    self.subTest(
                        readiness_timeout=readiness_timeout,
                        poll_seconds=poll_seconds,
                    ),
                    self.assertRaises(ValueError),
                ):
                    waiter.run_service_wait(
                        [sys.executable, "-c", "raise SystemExit(0)"],
                        [sys.executable, "-c", "raise SystemExit(0)"],
                        readiness_timeout_seconds=readiness_timeout,
                        poll_seconds=poll_seconds,
                        max_log_bytes=1024,
                        output_path=root / "terminal.json",
                        ready_output_path=root / "ready.json",
                    )


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
