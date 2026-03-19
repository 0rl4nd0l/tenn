"""Worker layer contracts and dispatch utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from autodev.runtime.config import AutoDevConfig
from autodev.runtime.task_queue import Task


WorkerStatus = Literal["no_change", "changed", "blocked", "error"]


@dataclass(frozen=True)
class WorkerRequest:
    task_id: str
    task_slug: str
    task_description: str
    allowed_paths: tuple[str, ...]
    repo_root: Path
    branch_name: str
    max_changed_lines_per_attempt: int
    max_changed_files_per_attempt: int
    allow_network: bool = False
    llm_routing_mode: str = "simple"
    llm_provider_balanced: str = "llamacpp"
    llm_provider_heavy: str = "llamacpp"
    llama_cpp_base_url: str = "http://127.0.0.1:8000/v1"
    llama_cpp_api_key: str = "local-openai-key"
    llama_cpp_model_balanced: str = "qwen2.5-coder-14b"
    llama_cpp_model_heavy: str = "qwen2.5-coder-14b"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model_balanced: str = "qwen2.5-coder:7b"
    ollama_model_heavy: str = "qwen2.5:32b"
    ollama_timeout_seconds: int = 120
    openai_model: str = "gpt-4.1-mini"
    llm_max_generation_attempts: int = 3
    protected_paths: tuple[str, ...] = ()
    run_dir: Path | None = None
    attempt_index: int = 1


@dataclass(frozen=True)
class WorkerResult:
    status: WorkerStatus
    summary: str
    files_changed: list[str]
    lines_changed: int
    commit_created: bool
    block_reason: dict[str, Any] | None = None
    artifacts: list[str] | None = None


def list_workers() -> list[str]:
    return ["local_patch", "llm_patch"]


def select_worker(config: AutoDevConfig, task: Task) -> str:
    _ = task
    selected = config.worker_name.strip()
    if selected in list_workers():
        return selected
    return "local_patch"


def run_worker(request: WorkerRequest, worker_name: str) -> WorkerResult:
    if worker_name == "local_patch":
        from autodev.runtime.workers.local_patch_worker import run_local_patch_worker

        return run_local_patch_worker(request)
    if worker_name == "llm_patch":
        from autodev.runtime.workers.llm_patch_worker import run_llm_patch_worker

        return run_llm_patch_worker(request)
    return WorkerResult(
        status="blocked",
        summary=f"Unsupported worker '{worker_name}'.",
        files_changed=[],
        lines_changed=0,
        commit_created=False,
        block_reason={
            "reason": "unsupported_worker",
            "worker_name": worker_name,
        },
        artifacts=[],
    )
