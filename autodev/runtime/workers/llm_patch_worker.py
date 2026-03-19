"""LLM-based patch worker using file edits and git-generated diffs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

from autodev.runtime.repo_rag import load_context, search_repository
from autodev.runtime.repo_ops import diff_numstat
from autodev.runtime.worker_interface import WorkerRequest, WorkerResult

HEAVY_TASK_HINTS = (
    "architecture",
    "cross-file",
    "multi-file",
    "multi module",
    "multiple files",
    "orchestr",
    "pipeline",
    "refactor",
    "system",
    "worker",
)
try:
    MAX_REPO_TREE_FILES = int(os.getenv("AUTODEV_LLM_REPO_TREE_FILES", "80"))
except ValueError:
    MAX_REPO_TREE_FILES = 80
try:
    RAG_TOP_K = int(os.getenv("AUTODEV_LLM_RAG_TOP_K", "3"))
except ValueError:
    RAG_TOP_K = 3
try:
    OLLAMA_NUM_PREDICT = int(os.getenv("AUTODEV_OLLAMA_NUM_PREDICT", "800"))
except ValueError:
    OLLAMA_NUM_PREDICT = 800
try:
    OLLAMA_TEMPERATURE = float(os.getenv("AUTODEV_OLLAMA_TEMPERATURE", "0"))
except ValueError:
    OLLAMA_TEMPERATURE = 0.0


@dataclass(frozen=True)
class ModelSelection:
    provider: str
    model: str
    profile: str
    reason: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_log(path: Path | None, message: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def _prompt_with_rag_context(task: str, relevant_files: list[str], code_context: str) -> str:
    files_block = "\n".join(relevant_files) if relevant_files else "(no relevant files found)"
    context_block = code_context if code_context else "(no context loaded)"
    return (
        "TASK\n"
        f"{task}\n\n"
        "RELEVANT FILES\n"
        f"{files_block}\n\n"
        "CODE CONTEXT\n"
        f"{context_block}\n\n"
        "INSTRUCTIONS\n"
        "Modify only files that appear in the repository.\n"
        "Return FILE blocks only."
    )


def _tracked_repo_files(repo_path: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=repo_path,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to read repository file list.")
    return result.stdout.splitlines()


def get_repo_tree(repo_path: Path) -> str:
    files = _tracked_repo_files(repo_path)
    files = files[: max(1, MAX_REPO_TREE_FILES)]
    return "\n".join(files)


def _prompt_for_task(task: str, repo_tree: str) -> str:
    return f"""
You are a senior software engineer working in this repository.

Repository files:

{repo_tree}

Task:
{task}

Output format:

FILE: relative/path/from/repo/root
<full updated file contents>

Rules:
- Only modify files that exist in the repository
- Paths must match the repository tree above
- Output only FILE blocks
- No explanations
""".strip()


def _repair_prompt(text: str) -> str:
    return f"""
Convert the following output into FILE blocks with this format:

FILE: path/to/file
<full updated file contents>

Only output FILE blocks.

{text}
""".strip()


def _invalid_path_prompt(text: str, repo_tree: str, invalid_paths: list[str]) -> str:
    invalid_joined = "\n".join(invalid_paths)
    return f"""
Invalid file path.

Invalid entries:
{invalid_joined}

Only allowed files are:

{repo_tree}

Fix the output.

Output format:
FILE: relative/path/from/repo/root
<full updated file contents>

Output only FILE blocks.

{text}
""".strip()


def _strip_code_fences(text: str) -> str:
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def extract_file_blocks(text: str) -> dict[str, str]:
    pattern = r"^FILE:\s*(.+?)\n([\s\S]*?)(?=^FILE:|\Z)"
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    files: dict[str, str] = {}
    for path_raw, content_raw in matches:
        path = path_raw.strip()
        if not path:
            continue
        content = content_raw.lstrip("\n").rstrip("\n")
        files[path] = content + "\n"
    return files


def _select_model(task: str, request: WorkerRequest) -> ModelSelection:
    routing_mode = request.llm_routing_mode.strip().lower()
    task_lower = task.lower()
    balanced_provider = request.llm_provider_balanced.strip().lower() or "llamacpp"
    heavy_provider = request.llm_provider_heavy.strip().lower() or balanced_provider

    if routing_mode in {"off", "disabled", "single"}:
        return ModelSelection(
            provider=balanced_provider,
            model=(
                request.llama_cpp_model_balanced
                if balanced_provider == "llamacpp"
                else request.ollama_model_balanced
            ),
            profile="balanced",
            reason="routing disabled",
        )

    for hint in HEAVY_TASK_HINTS:
        if hint in task_lower:
            return ModelSelection(
                provider=heavy_provider,
                model=(
                    request.llama_cpp_model_heavy
                    if heavy_provider == "llamacpp"
                    else request.ollama_model_heavy
                ),
                profile="heavy",
                reason=f"matched task hint '{hint}'",
            )

    return ModelSelection(
        provider=balanced_provider,
        model=(
            request.llama_cpp_model_balanced
            if balanced_provider == "llamacpp"
            else request.ollama_model_balanced
        ),
        profile="balanced",
        reason="default code-edit profile",
    )


def run_llamacpp(prompt: str, selection: ModelSelection, request: WorkerRequest) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=request.llama_cpp_api_key,
        base_url=request.llama_cpp_base_url.rstrip("/"),
    )
    response = client.chat.completions.create(
        model=selection.model,
        messages=[{"role": "user", "content": prompt}],
        temperature=OLLAMA_TEMPERATURE,
        max_tokens=max(64, OLLAMA_NUM_PREDICT),
    )
    if not response.choices:
        raise RuntimeError("llama.cpp returned no choices.")
    message = response.choices[0].message
    output = (message.content or "").strip()
    if not output:
        raise RuntimeError("llama.cpp returned an empty response.")
    return output


def run_ollama(
    prompt: str,
    selection: ModelSelection,
    request: WorkerRequest,
    *,
    call_label: str,
    progress_log: Path | None = None,
    stream_log: Path | None = None,
) -> str:
    payload = json.dumps(
        {
            "model": selection.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max(64, OLLAMA_NUM_PREDICT),
                "temperature": OLLAMA_TEMPERATURE,
            },
        }
    ).encode("utf-8")
    endpoint = request.ollama_host.rstrip("/") + "/api/generate"
    http_request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    _append_log(
        progress_log,
        (
            f"{_utc_now()} call={call_label} event=start provider=ollama "
            f"model={selection.model} prompt_chars={len(prompt)} timeout={request.ollama_timeout_seconds}"
        ),
    )
    try:
        open_kwargs: dict[str, object] = {}
        if request.ollama_timeout_seconds > 0:
            open_kwargs["timeout"] = request.ollama_timeout_seconds
        with urllib.request.urlopen(http_request, **open_kwargs) as response:
            chunks: list[str] = []
            total_chars = 0
            chunk_count = 0
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError("Ollama API returned invalid streamed JSON.") from exc
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                text = str(data.get("response", ""))
                if text:
                    chunks.append(text)
                    total_chars += len(text)
                    chunk_count += 1
                    if stream_log is not None:
                        stream_log.parent.mkdir(parents=True, exist_ok=True)
                        with stream_log.open("a", encoding="utf-8") as handle:
                            handle.write(text)
                    _append_log(
                        progress_log,
                        (
                            f"{_utc_now()} call={call_label} event=chunk "
                            f"chunk={chunk_count} total_chars={total_chars}"
                        ),
                    )
                if bool(data.get("done", False)):
                    output = "".join(chunks).strip()
                    _append_log(
                        progress_log,
                        (
                            f"{_utc_now()} call={call_label} event=done "
                            f"chunks={chunk_count} output_chars={len(output)}"
                        ),
                    )
                    if not output:
                        raise RuntimeError("Ollama API returned an empty response.")
                    return output
    except urllib.error.URLError as exc:
        _append_log(progress_log, f"{_utc_now()} call={call_label} event=error detail={exc}")
        raise RuntimeError(f"Ollama API request failed: {exc}") from exc
    except TimeoutError as exc:
        _append_log(
            progress_log,
            f"{_utc_now()} call={call_label} event=timeout seconds={request.ollama_timeout_seconds}",
        )
        raise RuntimeError(f"Ollama API timed out after {request.ollama_timeout_seconds}s") from exc
    raise RuntimeError("Ollama API stream ended without a completion event.")


def run_openai(prompt: str, request: WorkerRequest) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.responses.create(
        model=request.openai_model,
        input=prompt,
    )
    output = getattr(response, "output_text", "")
    if not output:
        raise RuntimeError("OpenAI returned an empty response.")
    return output.strip()


def _run_model(
    prompt: str,
    allow_network: bool,
    selection: ModelSelection,
    request: WorkerRequest,
    call_label: str,
    progress_log: Path | None = None,
    stream_log: Path | None = None,
) -> str:
    try:
        if selection.provider == "llamacpp":
            _append_log(
                progress_log,
                (
                    f"{_utc_now()} call={call_label} event=start provider=llamacpp "
                    f"model={selection.model} prompt_chars={len(prompt)}"
                ),
            )
            output = run_llamacpp(prompt, selection=selection, request=request)
            if stream_log is not None:
                stream_log.parent.mkdir(parents=True, exist_ok=True)
                stream_log.write_text(output, encoding="utf-8")
            _append_log(
                progress_log,
                (
                    f"{_utc_now()} call={call_label} event=done "
                    f"provider=llamacpp output_chars={len(output)}"
                ),
            )
            return output

        return run_ollama(
            prompt,
            selection=selection,
            request=request,
            call_label=call_label,
            progress_log=progress_log,
            stream_log=stream_log,
        )
    except Exception as provider_error:
        if allow_network and os.getenv("OPENAI_API_KEY"):
            return run_openai(prompt, request=request)
        raise RuntimeError(f"LLM generation failed: {provider_error}") from provider_error


def _repair_output(
    text: str,
    allow_network: bool,
    selection: ModelSelection,
    request: WorkerRequest,
    call_label: str,
    progress_log: Path | None = None,
    stream_log: Path | None = None,
) -> str:
    return _run_model(
        _repair_prompt(text),
        allow_network=allow_network,
        selection=selection,
        request=request,
        call_label=call_label,
        progress_log=progress_log,
        stream_log=stream_log,
    )


def _validate_file_blocks(
    files: dict[str, str],
    known_files: set[str],
) -> tuple[dict[str, str], list[str]]:
    normalized: dict[str, str] = {}
    invalid_paths: list[str] = []
    for raw_path, content in files.items():
        try:
            rel_path = _normalize_path(raw_path)
        except RuntimeError:
            invalid_paths.append(raw_path.strip())
            continue
        if rel_path not in known_files:
            invalid_paths.append(rel_path)
            continue
        normalized[rel_path] = content
    return normalized, invalid_paths


def generate_file_edits(
    task: str,
    repo_path: Path,
    allow_network: bool,
    selection: ModelSelection,
    request: WorkerRequest,
    progress_log: Path | None = None,
    stream_log: Path | None = None,
) -> dict[str, str]:
    tracked_files = _tracked_repo_files(repo_path)
    repo_tree = "\n".join(tracked_files[: max(1, MAX_REPO_TREE_FILES)])
    known_files = {line.strip() for line in tracked_files if line.strip()}
    relevant_files = search_repository(task, top_k=max(1, RAG_TOP_K), repo_path=repo_path)
    rag_context = load_context(relevant_files, repo_path=repo_path)
    task_with_context = _prompt_with_rag_context(task, relevant_files, rag_context)
    prompt = _prompt_for_task(task_with_context, repo_tree)
    last_output = ""
    for attempt_index in range(1, max(1, request.llm_max_generation_attempts) + 1):
        primary = _strip_code_fences(
            _run_model(
                prompt,
                allow_network=allow_network,
                selection=selection,
                request=request,
                call_label=f"attempt_{attempt_index}_primary",
                progress_log=progress_log,
                stream_log=stream_log,
            )
        )
        last_output = primary
        primary_files = extract_file_blocks(primary)
        primary_valid, primary_invalid = _validate_file_blocks(primary_files, known_files)
        if primary_valid and not primary_invalid:
            return primary_valid

        repaired = _strip_code_fences(
            _repair_output(
                primary,
                allow_network=allow_network,
                selection=selection,
                request=request,
                call_label=f"attempt_{attempt_index}_repair",
                progress_log=progress_log,
                stream_log=stream_log,
            )
        )
        last_output = repaired
        repaired_files = extract_file_blocks(repaired)
        repaired_valid, repaired_invalid = _validate_file_blocks(repaired_files, known_files)
        if repaired_valid and not repaired_invalid:
            return repaired_valid

        invalid_paths = primary_invalid or repaired_invalid
        if invalid_paths:
            fixed = _strip_code_fences(
                _run_model(
                    _invalid_path_prompt(repaired, repo_tree, invalid_paths),
                    allow_network=allow_network,
                    selection=selection,
                    request=request,
                    call_label=f"attempt_{attempt_index}_invalid_path_repair",
                    progress_log=progress_log,
                    stream_log=stream_log,
                )
            )
            last_output = fixed
            fixed_files = extract_file_blocks(fixed)
            fixed_valid, fixed_invalid = _validate_file_blocks(fixed_files, known_files)
            if fixed_valid and not fixed_invalid:
                return fixed_valid

    raise RuntimeError(
        "Failed to generate file edits"
        + (f"; last_output_sample={last_output[:200]!r}" if last_output else "")
    )


def _normalize_path(path: str) -> str:
    path_obj = Path(path)
    if path_obj.is_absolute():
        raise RuntimeError(f"Absolute file path is not allowed: {path}")
    if ".." in path_obj.parts:
        raise RuntimeError(f"Path traversal is not allowed: {path}")
    normalized = path_obj.as_posix().lstrip("./")
    if not normalized:
        raise RuntimeError("Empty file path from model output.")
    return normalized


def _is_allowed_path(path: str, allowed_paths: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in allowed_paths)


def _write_files(repo_root: Path, files: dict[str, str], allowed_paths: tuple[str, ...]) -> list[str]:
    written: list[str] = []
    for raw_path, content in files.items():
        rel_path = _normalize_path(raw_path)
        if not _is_allowed_path(rel_path, allowed_paths):
            raise RuntimeError(f"Path outside allowed scope: {rel_path}")
        abs_path = repo_root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
        written.append(rel_path)
    return sorted(set(written))


def _run_git(repo_root: Path, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or f"git {' '.join(args)} failed").strip()
        raise RuntimeError(detail)
    return proc


def _build_patch_from_edits(repo_root: Path, edited_paths: list[str]) -> str:
    if not edited_paths:
        return ""
    staged_before = _run_git(repo_root, ["diff", "--cached", "--name-only", "--", *edited_paths], check=False)
    if staged_before.stdout.strip():
        raise RuntimeError("Cannot build patch: one or more edited paths are already staged.")

    _run_git(repo_root, ["add", "--", *edited_paths], check=True)
    try:
        diff_proc = _run_git(repo_root, ["diff", "--cached", "--", *edited_paths], check=False)
        return diff_proc.stdout
    finally:
        _run_git(repo_root, ["restore", "--staged", "--", *edited_paths], check=True)


def _validate_patch(repo_root: Path, patch_rel: str) -> None:
    try:
        subprocess.run(
            ["git", "apply", "--check", "--cached", patch_rel],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git apply --check failed").strip()
        raise RuntimeError(detail) from exc


def run_llm_patch_worker(request: WorkerRequest) -> WorkerResult:
    work_dir = request.repo_root / "autodev_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    patch_abs = work_dir / "llm_patch.diff"
    patch_rel = str(patch_abs.relative_to(request.repo_root))
    meta_abs = work_dir / "llm_patch_meta.json"
    meta_rel = str(meta_abs.relative_to(request.repo_root))
    progress_abs = work_dir / "llm_patch_progress.log"
    progress_rel = str(progress_abs.relative_to(request.repo_root))
    stream_abs = work_dir / "llm_patch_stream.txt"
    stream_rel = str(stream_abs.relative_to(request.repo_root))
    before = diff_numstat(request.repo_root)
    selection = _select_model(request.task_description, request)
    progress_abs.write_text("", encoding="utf-8")
    stream_abs.write_text("", encoding="utf-8")
    meta_abs.write_text(
        json.dumps(
            {
                "provider": selection.provider,
                "model": selection.model,
                "profile": selection.profile,
                "reason": selection.reason,
                "routing_mode": request.llm_routing_mode,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        file_edits = generate_file_edits(
            request.task_description,
            repo_path=request.repo_root,
            allow_network=request.allow_network,
            selection=selection,
            request=request,
            progress_log=progress_abs,
            stream_log=stream_abs,
        )
        edited_paths = _write_files(request.repo_root, file_edits, request.allowed_paths)
        patch_text = _build_patch_from_edits(request.repo_root, edited_paths)
        patch_abs.write_text(patch_text.rstrip() + ("\n" if patch_text else ""), encoding="utf-8")
        if patch_text.strip():
            _validate_patch(request.repo_root, patch_rel)
    except Exception as exc:
        return WorkerResult(
            status="error",
            summary=(
                f"Failed to generate/apply LLM patch via {selection.model} "
                f"({selection.profile}): {exc}"
            ),
            files_changed=[],
            lines_changed=0,
            commit_created=False,
            block_reason={
                "reason": "llm_patch_failed",
                "error": str(exc),
                "model": selection.model,
                "profile": selection.profile,
            },
            artifacts=[
                item
                for item in (
                    patch_rel if patch_abs.exists() else None,
                    meta_rel,
                    progress_rel,
                    stream_rel,
                )
                if item
            ],
        )

    after = diff_numstat(request.repo_root)
    files_changed: list[str] = []
    lines_changed = 0
    for path, (after_add, after_del) in after.items():
        before_add, before_del = before.get(path, (0, 0))
        delta = max(0, after_add - before_add) + max(0, after_del - before_del)
        if delta > 0:
            files_changed.append(path)
            lines_changed += delta
    files_changed = sorted(set(files_changed))

    if not files_changed:
        return WorkerResult(
            status="no_change",
            summary=(
                f"Generated patch via LLM worker using {selection.model} "
                f"({selection.profile}) but no repository changes were applied."
            ),
            files_changed=[],
            lines_changed=0,
            commit_created=False,
            block_reason=None,
            artifacts=[patch_rel, meta_rel, progress_rel, stream_rel],
        )

    return WorkerResult(
        status="changed",
        summary=f"Generated patch via LLM worker using {selection.model} ({selection.profile})",
        files_changed=files_changed,
        lines_changed=lines_changed,
        commit_created=False,
        block_reason=None,
        artifacts=[patch_rel, meta_rel, progress_rel, stream_rel],
    )
