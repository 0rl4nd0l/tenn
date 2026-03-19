"""Deterministic local worker with safe default edit scope."""

from __future__ import annotations

from autodev.runtime.repo_ops import diff_numstat
from autodev.runtime.worker_interface import WorkerRequest, WorkerResult


def _sum_lines(stats: dict[str, tuple[int, int]]) -> int:
    return sum(added + deleted for added, deleted in stats.values())


def _is_path_allowed(path: str, allowed_paths: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in allowed_paths)


def _is_path_protected(path: str, protected_paths: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in protected_paths)


def run_local_patch_worker(request: WorkerRequest) -> WorkerResult:
    output_dir = request.repo_root / "autodev" / "worker_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    target_rel = f"autodev/worker_outputs/{request.task_slug}.md"
    target_abs = request.repo_root / target_rel

    if _is_path_protected(target_rel, request.protected_paths):
        return WorkerResult(
            status="blocked",
            summary="Worker target is in protected path.",
            files_changed=[],
            lines_changed=0,
            commit_created=False,
            block_reason={"reason": "protected_path", "path": target_rel},
            artifacts=[],
        )

    if not _is_path_allowed(target_rel, request.allowed_paths):
        return WorkerResult(
            status="blocked",
            summary="Worker target is outside allowed paths.",
            files_changed=[],
            lines_changed=0,
            commit_created=False,
            block_reason={"reason": "outside_allowed_paths", "path": target_rel},
            artifacts=[],
        )

    content = "\n".join(
        [
            "# Local Patch Worker Output",
            "",
            f"- task_id: {request.task_id}",
            f"- task_slug: {request.task_slug}",
            f"- branch: {request.branch_name}",
            f"- attempt: {request.attempt_index}",
            f"- allow_network: {request.allow_network}",
            "",
            "Deterministic worker artifact for autonomous loop integration.",
            "",
        ]
    )
    previous = target_abs.read_text(encoding="utf-8") if target_abs.exists() else ""
    if previous == content:
        return WorkerResult(
            status="no_change",
            summary="Deterministic worker content already up to date.",
            files_changed=[],
            lines_changed=0,
            commit_created=False,
            block_reason=None,
            artifacts=[target_rel],
        )

    before_stats = diff_numstat(request.repo_root)
    target_abs.write_text(content, encoding="utf-8")
    after_stats = diff_numstat(request.repo_root)
    files_changed: list[str] = []
    lines_changed = 0
    for path, (after_add, after_del) in after_stats.items():
        before_add, before_del = before_stats.get(path, (0, 0))
        delta = max(0, after_add - before_add) + max(0, after_del - before_del)
        if delta > 0:
            files_changed.append(path)
            lines_changed += delta
    if target_rel not in files_changed:
        files_changed.append(target_rel)
        lines_changed += content.count("\n")
    files_changed = sorted(set(files_changed))
    return WorkerResult(
        status="changed",
        summary="Applied deterministic local patch worker update.",
        files_changed=files_changed,
        lines_changed=lines_changed,
        commit_created=False,
        block_reason=None,
        artifacts=[target_rel],
    )
