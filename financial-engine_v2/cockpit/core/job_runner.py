from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cockpit.core.types import JobRun


class JobRunner:
    def __init__(self, repo_root: Path, logs_dir: Path) -> None:
        self.repo_root = repo_root
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._active_proc: asyncio.subprocess.Process | None = None
        self._active_job_id: str | None = None

    @property
    def active_job_id(self) -> str | None:
        return self._active_job_id

    async def cancel_active(self) -> str:
        proc = self._active_proc
        if proc is None:
            return "none"
        if proc.returncode is not None:
            return "already_exited"

        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
            return "terminated"
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "killed"

    async def run(
        self,
        job: JobRun,
        command: list[str],
        timeout_seconds: int,
        env: dict[str, str] | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> JobRun:
        stdout_path = self.logs_dir / f"{job.job_id}.out.log"
        stderr_path = self.logs_dir / f"{job.job_id}.err.log"
        job.stdout_path = str(stdout_path)
        job.stderr_path = str(stderr_path)
        job.status = "running"

        env_vars = os.environ.copy()
        if env:
            env_vars.update(env)

        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            proc = await asyncio.create_subprocess_exec(
                *command,
                cwd=str(self.repo_root),
                env=env_vars,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._active_proc = proc
            self._active_job_id = job.job_id

            async def _pump(reader: asyncio.StreamReader | None, sink, prefix: str) -> None:
                if reader is None:
                    return
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    sink.write(line)
                    sink.flush()
                    if on_output:
                        text = line.decode("utf-8", errors="replace").rstrip()
                        on_output(f"[{prefix}] {text}")

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        _pump(proc.stdout, stdout_file, "out"),
                        _pump(proc.stderr, stderr_file, "err"),
                    ),
                    timeout=timeout_seconds,
                )
                rc = await proc.wait()
                job.exit_code = rc
                job.status = "success" if rc == 0 else "failed"
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                job.status = "failed"
                job.exit_code = 124
                if on_output:
                    on_output(f"[err] timeout after {timeout_seconds}s")
            finally:
                if self._active_proc is proc:
                    self._active_proc = None
                    self._active_job_id = None

        job.ended_at = datetime.now(timezone.utc)
        return job
