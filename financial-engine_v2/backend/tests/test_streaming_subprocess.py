"""Integration tests for _run_action_subprocess_streaming.

Validates that subprocess output reaches log files incrementally
(not buffered until exit) and that progress callbacks fire correctly.
"""

from __future__ import annotations

import sys
import textwrap
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.routes.cockpit_api import _run_action_subprocess_streaming


class TestStreamingSubprocess:
    def test_output_reaches_file_before_process_exits(self, tmp_path: Path) -> None:
        """Log file grows while process is still running."""
        script = tmp_path / "slow_emit.py"
        script.write_text(
            textwrap.dedent("""\
                import time, sys
                for i in range(5):
                    print(f"line {i}", flush=True)
                    time.sleep(0.15)
                print("done", flush=True)
            """)
        )
        stdout_path = tmp_path / "out.log"
        stderr_path = tmp_path / "err.log"

        exit_code, stdout_text, _ = _run_action_subprocess_streaming(
            job_id="test-output-reaches-file",
            normalized_command=[sys.executable, str(script)],
            repo_root=tmp_path,
            action_env={},
            timeout_seconds=10,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

        assert exit_code == 0
        assert "line 0" in stdout_text
        assert "done" in stdout_text
        assert stdout_path.read_text().strip() == stdout_text.strip()

    def test_progress_callback_fires(self, tmp_path: Path) -> None:
        script = tmp_path / "emit_progress.py"
        script.write_text(
            textwrap.dedent("""\
                print("[progress] ticker_index=1/3 ticker=BHP", flush=True)
                print("some other output", flush=True)
                print("[progress] ticker_index=2/3 ticker=CSL", flush=True)
                print("[backfill] CSL done found=5 inserted=3", flush=True)
                print("[progress] ticker_index=3/3 ticker=WOW", flush=True)
            """)
        )
        stdout_path = tmp_path / "out.log"
        stderr_path = tmp_path / "err.log"
        captured_lines: list[str] = []

        _run_action_subprocess_streaming(
            job_id="test-progress-callback",
            normalized_command=[sys.executable, str(script)],
            repo_root=tmp_path,
            action_env={},
            timeout_seconds=10,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            on_stdout_line=lambda line: captured_lines.append(line.strip()),
        )

        assert len(captured_lines) == 5
        assert "[progress] ticker_index=1/3" in captured_lines[0]

    def test_timeout_kills_process(self, tmp_path: Path) -> None:
        script = tmp_path / "hang.py"
        script.write_text(
            textwrap.dedent("""\
                import time
                print("started", flush=True)
                time.sleep(60)
            """)
        )
        stdout_path = tmp_path / "out.log"
        stderr_path = tmp_path / "err.log"

        exit_code, _, stderr_text = _run_action_subprocess_streaming(
            job_id="test-timeout-kills-process",
            normalized_command=[sys.executable, str(script)],
            repo_root=tmp_path,
            action_env={},
            timeout_seconds=1,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

        assert exit_code == 124
        assert "timed out" in stderr_text.lower()

    def test_stderr_captured_to_file(self, tmp_path: Path) -> None:
        script = tmp_path / "emit_stderr.py"
        script.write_text(
            textwrap.dedent("""\
                import sys
                print("stdout line", flush=True)
                print("stderr line", file=sys.stderr, flush=True)
            """)
        )
        stdout_path = tmp_path / "out.log"
        stderr_path = tmp_path / "err.log"

        _run_action_subprocess_streaming(
            job_id="test-stderr-captured",
            normalized_command=[sys.executable, str(script)],
            repo_root=tmp_path,
            action_env={},
            timeout_seconds=10,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

        assert "stdout line" in stdout_path.read_text()
        assert "stderr line" in stderr_path.read_text()

    def test_nonzero_exit_code_preserved(self, tmp_path: Path) -> None:
        script = tmp_path / "fail.py"
        script.write_text("import sys; print('failing'); sys.exit(42)")
        stdout_path = tmp_path / "out.log"
        stderr_path = tmp_path / "err.log"

        exit_code, _, _ = _run_action_subprocess_streaming(
            job_id="test-nonzero-exit",
            normalized_command=[sys.executable, str(script)],
            repo_root=tmp_path,
            action_env={},
            timeout_seconds=10,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

        assert exit_code == 42


class TestReadJobOutputTail:
    """Test the tail-reading helper for in-progress job logs."""

    def test_tail_reads_last_n_bytes(self, tmp_path: Path) -> None:
        from app.routes.cockpit_api import _read_job_output_tail

        log = tmp_path / "big.log"
        lines = [f"line {i:04d}\n" for i in range(1000)]
        log.write_text("".join(lines))

        result = _read_job_output_tail(str(log), max_bytes=200)
        assert len(result) < 250
        assert "line 0999" in result
        assert "line 0000" not in result

    def test_small_file_returned_in_full(self, tmp_path: Path) -> None:
        from app.routes.cockpit_api import _read_job_output_tail

        log = tmp_path / "small.log"
        log.write_text("hello\nworld\n")

        result = _read_job_output_tail(str(log), max_bytes=8000)
        assert result == "hello\nworld\n"

    def test_missing_file_returns_empty(self) -> None:
        from app.routes.cockpit_api import _read_job_output_tail

        assert _read_job_output_tail("/nonexistent/path.log") == ""

    def test_none_path_returns_empty(self) -> None:
        from app.routes.cockpit_api import _read_job_output_tail

        assert _read_job_output_tail(None) == ""
