#!/usr/bin/env python3
"""Certified no-write extraction replay runner for fixed Tenn guard cases."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
DEFAULT_MANIFEST = (
    REPO_ROOT / "financial-engine_v2" / "data" / "extraction_no_write_cases" / "guard_cases_v1.json"
)
CERTIFIED_MANIFEST_ROOT = REPO_ROOT / "financial-engine_v2" / "data" / "extraction_no_write_cases"
DEFAULT_SHARED_DATA_ROOT = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data")
DEFAULT_REPORT_DIR = (
    "reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay"
)
APPROVED_TMP_PREFIX = "/tmp/tenn-extraction-no-write-replay-"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
BASELINE_PROFILE = "baseline-no-write"
DOCLING_PROFILE = "docling-no-write"
SUPPORTED_PROFILES = {BASELINE_PROFILE, DOCLING_PROFILE}
APPROVED_VENV_RELATIVE_PYTHONS = (
    "financial-engine_v2/.venv/bin/python",
    "financial-engine_v2/.venv/bin/python3",
    ".venv/bin/python",
    ".venv/bin/python3",
)
REPORT_OUTPUTS = (
    "input_manifest.json",
    "replay_results.json",
    "side_effect_audit.json",
    "validation.json",
    "logs/replay.log",
)
SAFE_ENV_REPORT_KEYS = {
    "DATA_ROOT",
    "DATABASE_URL",
    "TASK_MODE",
    "AUTO_CREATE_TABLES",
    "ENABLE_EMBEDDINGS",
    "ENABLE_EMBEDDING_CACHE",
    "ENABLE_QDRANT",
    "ENABLE_MARKETINDEX_FALLBACK",
    "ENABLE_IMPORTANCE_CLASSIFICATION",
    "IMPORTANCE_MATERIALIZE_OUTPUT",
    "ENABLE_SESSION_MEMORY",
    "ROUTER_FEEDBACK_ENABLED",
    "OPENBB_SIDECAR_ENABLE_STAGING_WRITES",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "TENN_EXTRACTION_ACTIVE_FILE",
    "MODEL_ROUTING_CONFIG",
    "EXTRACTION_SKIP_NARRATIVE",
    "EXTRACTION_PARALLEL",
    "LLAMACPP_URL",
    "EXTRACTION_LLAMACPP_URL",
    "LLM_URL",
    "OLLAMA_URL",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "EXTRACT_MODEL",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONNOUSERSITE",
    "HOME",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
}
SECRET_ENV_REPORT_KEYS = {
    "ANTHROPIC_API_KEY",
    "LLM_API_KEY",
    "OPENAI_API_KEY",
}
METRIC_FIELDS = (
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
    "total_debt",
)


class ReplayConfigError(RuntimeError):
    """Raised when the no-write contract cannot be proven before replay."""


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(key): _jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_jsonable(item) for item in value]
        return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReplayConfigError(f"JSON root must be an object: {path}")
    return payload


def _normalize_repo_path(path_text: str) -> PurePosixPath:
    path = PurePosixPath(str(path_text).strip().replace("\\", "/"))
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ReplayConfigError(f"path must be repo-relative without parent segments: {path_text}")
    return path


def resolve_report_dir(report_dir: str, *, repo_root: Path = REPO_ROOT) -> Path:
    path = _normalize_repo_path(report_dir)
    if len(path.parts) < 3 or path.parts[:2] != ("reports", "agent_jobs"):
        raise ReplayConfigError("report dir must be under reports/agent_jobs/<job_id>")
    resolved = (repo_root / path).resolve()
    allowed_root = (repo_root / "reports" / "agent_jobs").resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise ReplayConfigError("resolved report dir escaped reports/agent_jobs") from exc
    for parent in (repo_root / "reports", allowed_root, allowed_root / path.parts[2]):
        if parent.exists() and parent.is_symlink():
            raise ReplayConfigError(f"report path parent must not be symlinked: {parent}")
    return resolved


def resolve_manifest_path(path: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    raw_path = Path(path)
    resolved = (repo_root / raw_path).resolve() if not raw_path.is_absolute() else raw_path.resolve()
    certified_root = CERTIFIED_MANIFEST_ROOT.resolve()
    try:
        resolved.relative_to(certified_root)
    except ValueError as exc:
        raise ReplayConfigError(
            f"case manifest must be under certified manifest root: {certified_root}"
        ) from exc
    if resolved.exists() and resolved.is_symlink():
        raise ReplayConfigError(f"case manifest must not be a symlink: {resolved}")
    return resolved


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = _read_json(path)
    if manifest.get("artifact_type") != "extraction_no_write_case_manifest_v1":
        raise ReplayConfigError("manifest artifact_type must be extraction_no_write_case_manifest_v1")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ReplayConfigError("manifest cases must be a non-empty list")
    seen: set[str] = set()
    required = {"case_id", "ticker", "document_id", "title", "source_path"}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ReplayConfigError(f"case[{index}] must be an object")
        missing = sorted(required - set(case))
        if missing:
            raise ReplayConfigError(f"case[{index}] missing fields: {', '.join(missing)}")
        case_id = str(case.get("case_id") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", case_id):
            raise ReplayConfigError(f"case[{index}] has invalid case_id: {case_id!r}")
        if case_id in seen:
            raise ReplayConfigError(f"duplicate case_id: {case_id}")
        seen.add(case_id)
        source_path = str(case.get("source_path") or "").strip()
        if not source_path:
            raise ReplayConfigError(f"case[{index}] source_path must be non-empty")
        if not Path(source_path).expanduser().is_absolute():
            _normalize_repo_path(source_path)
    certification = manifest.get("certification")
    if not isinstance(certification, dict):
        raise ReplayConfigError("manifest certification must be an object")
    if certification.get("allow_production_writes") is not False:
        raise ReplayConfigError("manifest must explicitly disallow production writes")
    if certification.get("loopback_llm_only") is not True:
        raise ReplayConfigError("manifest must require loopback-only LLM access")
    return manifest


def select_cases(manifest: dict[str, Any], selectors: list[str]) -> list[dict[str, Any]]:
    cases = manifest["cases"]
    if not selectors or selectors == ["all"] or "all" in selectors:
        return [dict(case) for case in cases]

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for selector in selectors:
        needle = selector.strip().lower()
        matches = [
            case
            for case in cases
            if needle
            and needle
            in {
                str(case.get("case_id", "")).lower(),
                str(case.get("ticker", "")).lower(),
                str(case.get("document_id", "")).lower(),
            }
        ]
        if not matches:
            raise ReplayConfigError(f"unknown or uncertified case selector: {selector}")
        for match in matches:
            case_id = str(match["case_id"])
            if case_id not in seen:
                selected.append(dict(match))
                seen.add(case_id)
    return selected


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        text = str(path.expanduser().resolve(strict=False))
        if text not in seen:
            unique.append(Path(text))
            seen.add(text)
    return unique


def _candidate_data_roots() -> list[Path]:
    candidates: list[Path] = []
    for env_key in ("DATA_ROOT",):
        value = os.environ.get(env_key)
        if value:
            candidates.append(Path(value))
    candidates.extend(
        [
            REPO_ROOT / "financial-engine_v2" / "data",
            DEFAULT_SHARED_DATA_ROOT,
        ]
    )
    return _unique_paths(candidates)


def _candidate_docs_roots() -> list[Path]:
    candidates: list[Path] = []
    value = os.environ.get("DOCS_ROOT")
    if value:
        candidates.append(Path(value))
    candidates.extend(data_root / "asx" / "docs" for data_root in _candidate_data_roots())
    return _unique_paths(candidates)


def _portable_source_suffixes(path_text: str) -> tuple[PurePosixPath | None, PurePosixPath | None]:
    rel = _normalize_repo_path(path_text)
    parts = rel.parts
    if len(parts) >= 2 and parts[:2] == ("asx", "docs"):
        return rel, PurePosixPath(*parts[2:])
    if len(parts) >= 3 and parts[:3] == ("data", "asx", "docs"):
        return PurePosixPath(*parts[1:]), PurePosixPath(*parts[3:])
    if len(parts) >= 4 and parts[:4] == ("financial-engine_v2", "data", "asx", "docs"):
        return PurePosixPath(*parts[2:]), PurePosixPath(*parts[4:])
    return None, None


def source_path_candidates(path_text: str) -> list[Path]:
    raw = Path(str(path_text).strip()).expanduser()
    if raw.is_absolute():
        return _unique_paths([raw])

    rel = _normalize_repo_path(path_text)
    candidates = [(REPO_ROOT / rel)]
    data_suffix, docs_suffix = _portable_source_suffixes(path_text)
    if data_suffix is not None:
        candidates.extend(data_root / data_suffix for data_root in _candidate_data_roots())
    if docs_suffix is not None:
        candidates.extend(docs_root / docs_suffix for docs_root in _candidate_docs_roots())
    return _unique_paths(candidates)


def resolve_source_path(path_text: str) -> tuple[Path, list[Path]]:
    candidates = source_path_candidates(path_text)
    for candidate in candidates:
        if candidate.exists():
            return candidate, candidates
    return candidates[0], candidates


def resolve_case_source_paths(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved_cases: list[dict[str, Any]] = []
    for case in cases:
        resolved, candidates = resolve_source_path(str(case["source_path"]))
        resolved_case = dict(case)
        original_source_path = str(resolved_case["source_path"])
        resolved_case["source_path"] = str(resolved)
        if original_source_path != str(resolved):
            resolved_case["source_path_original"] = original_source_path
        resolved_case["source_path_candidates"] = [str(candidate) for candidate in candidates]
        resolved_cases.append(resolved_case)
    return resolved_cases


def assert_loopback_url(raw_url: str) -> str:
    url = str(raw_url or "").strip().rstrip("/")
    if not url:
        raise ReplayConfigError("LLM URL is empty")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ReplayConfigError(f"LLM URL scheme must be http or https: {url}")
    if parsed.hostname not in LOOPBACK_HOSTS:
        raise ReplayConfigError(f"LLM URL must be loopback-only: {url}")
    return url


def normalize_profile(raw_profile: str) -> str:
    profile = str(raw_profile or BASELINE_PROFILE).strip()
    if profile not in SUPPORTED_PROFILES:
        raise ReplayConfigError(
            f"unsupported profile {profile!r}; expected one of {sorted(SUPPORTED_PROFILES)}"
        )
    return profile


def _abspath_no_symlink(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def approved_venv_candidates() -> list[Path]:
    return [_abspath_no_symlink(REPO_ROOT / relative_path) for relative_path in APPROVED_VENV_RELATIVE_PYTHONS]


def _resolve_path_no_symlink(path_text: str) -> Path:
    raw_path = Path(path_text).expanduser()
    if not raw_path.is_absolute():
        raw_path = REPO_ROOT / raw_path
    return _abspath_no_symlink(raw_path)


def resolve_approved_venv_python(path_text: str) -> Path:
    selected = _resolve_path_no_symlink(path_text)
    candidates = approved_venv_candidates()
    if selected not in candidates:
        candidate_text = ", ".join(str(candidate) for candidate in candidates)
        raise ReplayConfigError(
            f"venv python is not approved for certified no-write replay: {selected}; "
            f"approved candidates: {candidate_text}"
        )
    return selected


def _same_python_path(left: Path, right: Path) -> bool:
    return _abspath_no_symlink(left) == _abspath_no_symlink(right)


def _select_docling_venv_python(requested_venv_python: str) -> tuple[Path | None, dict[str, Any]]:
    info: dict[str, Any] = {
        "approved_candidates": [str(candidate) for candidate in approved_venv_candidates()],
        "current_python": sys.executable,
        "requested_venv_python": requested_venv_python or None,
    }
    current_python = _abspath_no_symlink(Path(sys.executable))
    for candidate in approved_venv_candidates():
        if _same_python_path(current_python, candidate):
            info["selected_venv_python"] = str(candidate)
            info["current_python_is_selected"] = True
            info["selected_exists"] = candidate.exists()
            info["selected_executable"] = os.access(candidate, os.X_OK)
            return candidate, info
    if requested_venv_python:
        selected = resolve_approved_venv_python(requested_venv_python)
        info["selected_venv_python"] = str(selected)
        info["current_python_is_selected"] = _same_python_path(current_python, selected)
        info["selected_exists"] = selected.exists()
        info["selected_executable"] = os.access(selected, os.X_OK)
        return selected, info
    for candidate in approved_venv_candidates():
        if candidate.exists() and os.access(candidate, os.X_OK):
            info["selected_venv_python"] = str(candidate)
            info["current_python_is_selected"] = _same_python_path(current_python, candidate)
            info["selected_exists"] = True
            info["selected_executable"] = True
            return candidate, info
    info["selected_venv_python"] = None
    info["current_python_is_selected"] = False
    info["selected_exists"] = False
    info["selected_executable"] = False
    return None, info


def _reexec_for_docling_profile(selected_python: Path, args: argparse.Namespace) -> None:
    argv = [str(selected_python), str(Path(__file__).resolve())] + sys.argv[1:]
    if not args.venv_python:
        argv.extend(["--venv-python", str(selected_python)])
    if not args._profile_reexeced:
        argv.append("--_profile-reexeced")
    env: dict[str, str] = {}
    for key in (
        "PATH",
        "LANG",
        "LC_ALL",
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "DATA_ROOT",
        "DOCS_ROOT",
        "LLM_API_KEY",
        "LLAMACPP_URL",
        "EXTRACTION_LLAMACPP_URL",
    ):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["TENN_EXTRACTION_NO_WRITE_PROFILE_REEXEC"] = "1"
    os.execve(str(selected_python), argv, env)


def prepare_profile_process(args: argparse.Namespace) -> tuple[str, dict[str, Any], str | None]:
    profile = normalize_profile(args.profile)
    profile_info: dict[str, Any] = {
        "profile": profile,
        "current_python": sys.executable,
        "reexeced": bool(args._profile_reexeced),
    }
    if profile != DOCLING_PROFILE:
        return profile, profile_info, None

    selected_python, venv_info = _select_docling_venv_python(args.venv_python)
    profile_info.update(venv_info)
    if selected_python is None:
        return profile, profile_info, "approved_docling_venv_python_missing"
    if not selected_python.exists():
        return profile, profile_info, f"approved_docling_venv_python_missing:{selected_python}"
    if not os.access(selected_python, os.X_OK):
        return profile, profile_info, f"approved_docling_venv_python_not_executable:{selected_python}"
    if not _same_python_path(Path(sys.executable), selected_python):
        if args._profile_reexeced:
            return profile, profile_info, f"docling_profile_reexec_failed:{selected_python}"
        _reexec_for_docling_profile(selected_python, args)
    return profile, profile_info, None


def _verify_docling_import() -> tuple[dict[str, Any], str | None]:
    info: dict[str, Any] = {"python": sys.executable}
    try:
        import docling  # type: ignore[import-not-found]

        info["available"] = True
        info["version"] = getattr(docling, "__version__", "unknown")
        return info, None
    except Exception as exc:
        info["available"] = False
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info, "docling_import_failed"


def _docling_incompatible_cases(cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    incompatible: list[dict[str, str]] = []
    for case in cases:
        parser_backend = str(case.get("parser_backend") or "docling")
        if parser_backend != "docling":
            incompatible.append(
                {
                    "case_id": str(case.get("case_id")),
                    "parser_backend": parser_backend,
                }
            )
    return incompatible


def _force_docling_profile_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    strict_cases: list[dict[str, Any]] = []
    for case in cases:
        strict_case = dict(case)
        strict_case["parser_backend"] = "docling"
        strict_case["strict_parser"] = True
        strict_cases.append(strict_case)
    return strict_cases


def _git_status() -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    rows = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.returncode != 0:
        rows.append(f"git_status_error:{proc.stderr.strip()}")
    return rows


def _git_status_path(row: str) -> str:
    text = row.rstrip()
    if not text.strip():
        return ""
    if text.startswith("git_status_error:"):
        return text
    path_text = text[3:] if len(text) >= 3 else text
    if " -> " in path_text:
        path_text = path_text.rsplit(" -> ", 1)[1]
    return path_text.strip().strip('"').replace("\\", "/")


def _report_dir_git_prefix(report_dir: Path) -> str | None:
    try:
        relative = report_dir.resolve().relative_to(REPO_ROOT.resolve())
        return relative.as_posix().rstrip("/") + "/"
    except ValueError:
        parts = PurePosixPath(str(report_dir).replace("\\", "/")).parts
        for index in range(len(parts) - 1):
            if parts[index : index + 2] == ("reports", "agent_jobs"):
                return PurePosixPath(*parts[index:]).as_posix().rstrip("/") + "/"
    return None


def _is_report_local_git_status(row: str, report_prefix: str | None) -> bool:
    if report_prefix is None:
        return False
    path = _git_status_path(row)
    return path == report_prefix.rstrip("/") or path.startswith(report_prefix)


def _unexpected_git_status_changes(
    git_before: list[str],
    git_after: list[str],
    report_dir: Path,
) -> list[str]:
    before = set(git_before)
    report_prefix = _report_dir_git_prefix(report_dir)
    return [
        row
        for row in git_after
        if row not in before and not _is_report_local_git_status(row, report_prefix)
    ]


def _repo_path_for_git_status(path_text: str) -> Path | None:
    if not path_text or path_text.startswith("git_status_error:"):
        return None
    path = (REPO_ROOT / path_text).resolve(strict=False)
    try:
        path.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return None
    return path


def _dirty_repo_file_snapshot(git_rows: list[str], report_dir: Path) -> dict[str, dict[str, Any]]:
    report_prefix = _report_dir_git_prefix(report_dir)
    snapshots: dict[str, dict[str, Any]] = {}
    for row in git_rows:
        if _is_report_local_git_status(row, report_prefix):
            continue
        path = _repo_path_for_git_status(_git_status_path(row))
        if path is None:
            continue
        try:
            rel = path.relative_to(REPO_ROOT.resolve()).as_posix()
        except ValueError:
            continue
        snapshots[rel] = _file_snapshot(path, hash_file=True)
    return snapshots


def _repo_file_snapshots(paths: list[str]) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for rel in paths:
        path = _repo_path_for_git_status(rel)
        if path is None:
            continue
        snapshots[rel] = _file_snapshot(path, hash_file=True)
    return snapshots


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_snapshot(path: Path, *, hash_file: bool = False) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    payload: dict[str, Any] = {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if hash_file:
        payload["sha256"] = _sha256(path)
    return payload


def _source_snapshot(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(case["case_id"]): _file_snapshot(Path(str(case["source_path"])), hash_file=True)
        for case in cases
    }


def _safe_cache_label(pdf_path: str) -> str:
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(pdf_path).name).strip("._")
    return label[:96] or "document"


def _cache_key_material(pdf_path: str) -> str:
    source_path = Path(pdf_path).expanduser()
    resolved = str(source_path.resolve(strict=False))
    try:
        stat = source_path.stat()
    except OSError:
        return f"path={resolved}"
    return f"path={resolved}\0size={stat.st_size}\0mtime_ns={stat.st_mtime_ns}"


def _cache_paths_for_root(cache_root: Path, pdf_path: str) -> dict[str, str]:
    digest = hashlib.sha256(_cache_key_material(pdf_path).encode("utf-8")).hexdigest()
    label = _safe_cache_label(pdf_path)
    return {
        "docling": str((cache_root / f"{digest}-{label}.docling.json").resolve()),
        "pymupdf": str((cache_root / f"{digest}-{label}.pymupdf.json").resolve()),
    }


def _data_root_from_source(path_text: str) -> Path | None:
    path = Path(path_text).expanduser().resolve(strict=False)
    parts = path.parts
    for index in range(len(parts) - 2):
        if parts[index : index + 3] == ("data", "asx", "docs"):
            return Path(*parts[: index + 1])
    return None


def _normal_cache_roots(cases: list[dict[str, Any]]) -> list[Path]:
    roots = {
        (REPO_ROOT / "financial-engine_v2" / "data" / "reports" / "extraction_cache" / "docling_extract").resolve()
    }
    for case in cases:
        data_root = _data_root_from_source(str(case["source_path"]))
        if data_root is not None:
            roots.add((data_root / "reports" / "extraction_cache" / "docling_extract").resolve())
    return sorted(roots)


def _normal_cache_snapshot(cases: list[dict[str, Any]], roots: list[Path]) -> dict[str, Any]:
    return {str(root): _list_files(root, hash_files=True) for root in roots}


def _list_files(root: Path, *, hash_files: bool = False) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(root.rglob("*")):
        if item.is_file():
            stat = item.stat()
            rows.append(
                {
                    "path": str(item),
                    "relative_path": str(item.relative_to(root)),
                    "size": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
            if hash_files:
                rows[-1]["sha256"] = _sha256(item)
    return rows


def _report_files(report_dir: Path) -> list[dict[str, Any]]:
    return _list_files(report_dir)


def _reset_report_outputs(report_dir: Path) -> None:
    report_root = report_dir.resolve()
    for relative_path in REPORT_OUTPUTS:
        target = (report_dir / relative_path).resolve()
        try:
            target.relative_to(report_root)
        except ValueError as exc:
            raise ReplayConfigError(f"report output escaped report dir: {relative_path}") from exc
        if target.exists():
            target.unlink()


def build_safe_env(data_root: Path, llm_url: str) -> dict[str, str]:
    env: dict[str, str] = {}
    for key in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        value = os.environ.get(key)
        if value:
            env[key] = value
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "HOME": str(data_root / "home"),
            "TMPDIR": str(data_root / "tmp"),
            "XDG_CACHE_HOME": str(data_root / "xdg" / "cache"),
            "XDG_CONFIG_HOME": str(data_root / "xdg" / "config"),
            "XDG_STATE_HOME": str(data_root / "xdg" / "state"),
            "DATA_ROOT": str(data_root),
            "DATABASE_URL": "sqlite:///:memory:",
            "DOCS_ROOT": str(data_root / "asx" / "docs"),
            "MARKETINDEX_ANNOUNCEMENTS_FILE": str(data_root / "raw" / "marketindex_announcements.json"),
            "IMPORTANCE_OUTPUT_ROOT": str(data_root / "asx" / "importance"),
            "TASK_MODE": "sync",
            "AUTO_CREATE_TABLES": "false",
            "ENABLE_EMBEDDINGS": "false",
            "ENABLE_EMBEDDING_CACHE": "false",
            "ENABLE_QDRANT": "false",
            "ENABLE_MARKETINDEX_FALLBACK": "false",
            "ENABLE_IMPORTANCE_CLASSIFICATION": "false",
            "IMPORTANCE_MATERIALIZE_OUTPUT": "false",
            "ENABLE_SESSION_MEMORY": "false",
            "ROUTER_FEEDBACK_ENABLED": "false",
            "OPENBB_SIDECAR_ENABLE_STAGING_WRITES": "false",
            "REDIS_URL": "memory://tenn-no-write",
            "CELERY_BROKER_URL": "memory://tenn-no-write",
            "CELERY_RESULT_BACKEND": "cache+memory://",
            "TENN_EXTRACTION_ACTIVE_FILE": str(data_root / "runtime" / "extraction_active.json"),
            "MODEL_ROUTING_CONFIG": str(REPO_ROOT / "financial-engine_v2" / "backend" / "app" / "config" / "model_routing.yaml"),
            "EXTRACTION_SKIP_NARRATIVE": "1",
            "EXTRACTION_PARALLEL": "0",
            "LLAMACPP_URL": llm_url,
            "EXTRACTION_LLAMACPP_URL": llm_url,
            "LLM_URL": llm_url,
            "OLLAMA_URL": "http://127.0.0.1:11434",
            "LLM_API_KEY": os.environ.get("LLM_API_KEY") or "local-openai-key",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "EXTRACT_MODEL": "model:qwen2.5-14b-instruct",
        }
    )
    return env


def apply_safe_env(env: dict[str, str]) -> None:
    unsafe_keys = {
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "DOCLING_PAGE_BATCH_PROFILE_PATH",
        "DOCLING_PAGE_BATCH_PROFILE_TARGET",
        "DOCLING_PAGE_BATCH_PROFILE_BATCH_SIZE",
        "TENN_AGENT_REGISTRY_ROOT",
    }
    for key in unsafe_keys:
        os.environ.pop(key, None)
    for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        value = env.get(key)
        if value:
            Path(value).mkdir(parents=True, exist_ok=True)
    for key, value in env.items():
        os.environ[key] = value


def _validate_source_files(cases: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for case in cases:
        path = Path(str(case["source_path"]))
        if not path.exists():
            candidates = case.get("source_path_candidates")
            suffix = f" candidates={candidates}" if candidates else ""
            missing.append(f"{case['case_id']}:{path}{suffix}")
    return missing


def _patch_runtime_side_effects(llm_module: Any) -> None:
    def no_op(*_args: Any, **_kwargs: Any) -> None:
        return None

    for attr in (
        "configure_metrics_snapshot",
        "record",
        "save_metrics_snapshot",
        "_flush_snapshot_async",
        "_schedule_snapshot_save",
    ):
        target = getattr(llm_module.router_metrics, attr, None)
        if target is not None:
            setattr(llm_module.router_metrics, attr, no_op)
    for attr in ("mark_task_started", "mark_task_finished"):
        target = getattr(llm_module.router_state, attr, None)
        if target is not None:
            setattr(llm_module.router_state, attr, no_op)
    if hasattr(llm_module, "_anthropic_api_key"):
        setattr(llm_module, "_anthropic_api_key", lambda: "")


def _install_write_sentinels() -> list[str]:
    installed: list[str] = []

    def blocked(name: str):
        def _raise(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError(f"no_write_replay_blocked_write_surface:{name}")

        return _raise

    try:
        from app.core import db as db_module

        db_module.SessionLocal = blocked("SessionLocal")
        installed.append("app.core.db.SessionLocal")
    except Exception:
        pass
    try:
        from app.services import embeddings as embeddings_module

        embeddings_module.QdrantClient = blocked("QdrantClient")
        installed.append("app.services.embeddings.QdrantClient")
    except Exception:
        pass
    try:
        from app.services import pipeline as pipeline_module

        pipeline_module.process_document = blocked("pipeline.process_document")
        installed.append("app.services.pipeline.process_document")
    except Exception:
        pass
    return installed


class Observer:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(
        self,
        stage: str,
        status: str,
        message: str,
        *,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "stage": stage,
                "status": status,
                "message": message,
                "error_code": error_code,
                "details": copy.deepcopy(details or {}),
            }
        )


def _build_client(llm_url: str) -> tuple[Any, dict[str, Any]]:
    import httpx

    base_url = assert_loopback_url(llm_url)
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "local-openai-key"
    client = httpx.Client(base_url=base_url, timeout=180.0, headers={"Authorization": f"Bearer {api_key}"})
    started = time.monotonic()
    response = client.get("/models")
    elapsed = time.monotonic() - started
    response.raise_for_status()
    return client, {
        "base_url": base_url,
        "has_api_key": bool(api_key),
        "models_status_code": response.status_code,
        "models_elapsed_s": round(elapsed, 3),
        "models_head": str(response.json())[:1200],
    }


def _compact_payload(result: Any) -> dict[str, Any]:
    payload = result.payload or {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    return {
        "status": result.status,
        "error": result.error,
        "period_type": payload.get("period_type"),
        "period_start": payload.get("period_start"),
        "period_end": payload.get("period_end"),
        "scale": payload.get("scale"),
        "currency": payload.get("currency"),
        "confidence_metrics": payload.get("confidence_metrics"),
        "non_null_metric_count": len([value for value in metrics.values() if value is not None]),
        "non_null_metrics": {key: value for key, value in metrics.items() if value is not None},
        "row_refs": payload.get("row_refs"),
        "metric_source_scales": payload.get("metric_source_scales"),
        "metric_scale_sources": payload.get("metric_scale_sources"),
        "provenance": payload.get("provenance"),
        "source_bound": payload.get("source_bound"),
        "source_period_end_evidence": payload.get("source_period_end_evidence"),
        "source_document_classification": payload.get("source_document_classification"),
        "structured_extraction": payload.get("_structured_extraction"),
        "scale_validation": payload.get("scale_validation"),
    }


def _case_metadata(case: dict[str, Any]) -> dict[str, str]:
    return {
        "document_id": str(case["document_id"]),
        "ticker": str(case["ticker"]),
        "title": str(case["title"]),
    }


def _run_cases(cases: list[dict[str, Any]], llm_url: str, log_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.services import llm as llm_module
    from app.services import multipass_extraction as mp

    _patch_runtime_side_effects(llm_module)
    sentinels = _install_write_sentinels()
    client = None
    llm_info: dict[str, Any] = {"write_sentinels": sentinels}
    results: list[dict[str, Any]] = []
    with log_path.open("a", encoding="utf-8") as log:
        try:
            client, llm_info = _build_client(llm_url)
            llm_info["write_sentinels"] = sentinels
            log.write(f"llm_ready {json.dumps(llm_info, sort_keys=True)}\n")
            for case in cases:
                observer = Observer()
                debug_capture: dict[str, Any] = {}
                started = time.monotonic()
                case_id = str(case["case_id"])
                log.write(f"case_start {case_id}\n")
                try:
                    result = mp.run_multipass_extraction(
                        str(case["source_path"]),
                        _case_metadata(case),
                        client,
                        skip_narrative=bool(case.get("skip_narrative", True)),
                        parser_backend=str(case.get("parser_backend") or "docling"),
                        strict_parser=bool(case.get("strict_parser", False)),
                        observer=observer,
                        debug_capture=debug_capture,
                        openability_pages=case.get("openability_pages"),
                        openability_selected_tables=bool(case.get("openability_selected_tables", False)),
                    )
                    payload = _compact_payload(result)
                    results.append(
                        {
                            "case_id": case_id,
                            "role": case.get("role"),
                            "ticker": case.get("ticker"),
                            "document_id": case.get("document_id"),
                            "source_path": case.get("source_path"),
                            "expected_status": case.get("expected_status"),
                            "expected_period_type": case.get("expected_period_type"),
                            "expected_period_end": case.get("expected_period_end"),
                            "elapsed_s": round(time.monotonic() - started, 3),
                            "observer_events": observer.events,
                            "debug_capture_keys": sorted(debug_capture),
                            "pass3a_result_count": len(debug_capture.get("pass3a_results") or []),
                            "result": payload,
                        }
                    )
                    log.write(f"case_done {case_id} status={result.status} error={result.error}\n")
                except Exception as exc:  # pragma: no cover - exercised by smoke runs
                    results.append(
                        {
                            "case_id": case_id,
                            "role": case.get("role"),
                            "ticker": case.get("ticker"),
                            "document_id": case.get("document_id"),
                            "source_path": case.get("source_path"),
                            "elapsed_s": round(time.monotonic() - started, 3),
                            "observer_events": observer.events,
                            "result": {
                                "status": "exception",
                                "error": f"{type(exc).__name__}: {exc}",
                                "traceback": traceback.format_exc(limit=20),
                            },
                        }
                    )
                    log.write(f"case_exception {case_id} {type(exc).__name__}: {exc}\n")
        finally:
            if client is not None:
                client.close()
    return results, llm_info


def _is_infrastructure_failure(row: dict[str, Any]) -> bool:
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    error = str(result.get("error") or "").lower()
    if not error:
        return False
    markers = (
        "must be set",
        "server_unavailable",
        "connection",
        "connect",
        "timeout",
        "http_",
        "no module named",
        "llamacpp",
        "ollama_url",
        "llamacpp_url",
    )
    return error.startswith(("pass1:", "pass3a:", "pass3b:")) and any(
        marker in error for marker in markers
    )


def _expectation_failures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for row in results:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        expected_status = row.get("expected_status")
        expected_period_type = row.get("expected_period_type")
        expected_period_end = row.get("expected_period_end")
        observed_status = result.get("status")
        observed_period_type = result.get("period_type")
        observed_period_end = result.get("period_end")
        mismatches: dict[str, dict[str, Any]] = {}
        if expected_status and observed_status != expected_status:
            mismatches["status"] = {"expected": expected_status, "observed": observed_status}
        if expected_period_type and observed_period_type != expected_period_type:
            mismatches["period_type"] = {"expected": expected_period_type, "observed": observed_period_type}
        if expected_period_end and observed_period_end != expected_period_end:
            mismatches["period_end"] = {"expected": expected_period_end, "observed": observed_period_end}
        if mismatches:
            failures.append({"case_id": row.get("case_id"), "mismatches": mismatches})
    return failures


def _check_cache_root(data_root: Path) -> tuple[bool, str, str | None, str]:
    sys.path.insert(0, str(BACKEND_ROOT))
    verification_mode = "docling_extract"
    try:
        from app.services.docling_extract import _extract_cache_root

        cache_root = _extract_cache_root().resolve()
    except ModuleNotFoundError as exc:
        verification_mode = f"settings_fallback_missing_dependency:{exc.name}"
        cache_root = (
            data_root
            / "reports"
            / "extraction_cache"
            / "docling_extract"
        ).resolve()
    try:
        cache_root.relative_to(data_root)
    except ValueError:
        return False, str(cache_root), f"cache root is outside isolated DATA_ROOT: {cache_root}", verification_mode
    return True, str(cache_root), None, verification_mode


def _surface_audit(
    *,
    git_before: list[str],
    git_after: list[str],
    source_before: dict[str, Any],
    source_after: dict[str, Any],
    normal_cache_before: dict[str, Any],
    normal_cache_after: dict[str, Any],
    report_dir: Path,
    report_files: list[dict[str, Any]],
    isolated_cache_root: Path,
    isolated_cache_files: list[dict[str, Any]],
    isolated_runtime_root: Path,
    isolated_runtime_files: list[dict[str, Any]],
    dirty_repo_before: dict[str, Any] | None = None,
    dirty_repo_after: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_pdf_write = source_before != source_after
    normal_parser_cache_write = normal_cache_before != normal_cache_after
    unexpected_git_changes = _unexpected_git_status_changes(git_before, git_after, report_dir)
    dirty_repo_file_mutations = (
        dirty_repo_before if dirty_repo_before is not None else {}
    ) != (dirty_repo_after if dirty_repo_after is not None else {})
    repo_worktree_write = bool(unexpected_git_changes) or dirty_repo_file_mutations
    allowed_report_prefix = str(report_dir) + os.sep
    report_only_durable_writes = all(
        str(row.get("path", "")).startswith(allowed_report_prefix) for row in report_files
    )
    isolated_prefix = str(isolated_cache_root) + os.sep
    isolated_cache_contained = all(
        str(row.get("path", "")).startswith(isolated_prefix) for row in isolated_cache_files
    )
    isolated_runtime_prefix = str(isolated_runtime_root) + os.sep
    isolated_runtime_contained = all(
        str(row.get("path", "")).startswith(isolated_runtime_prefix) for row in isolated_runtime_files
    )
    forbidden = {
        "source_pdf_write": source_pdf_write,
        "normal_parser_cache_write": normal_parser_cache_write,
        "db_write": False,
        "qdrant_write": False,
        "redis_write": False,
        "news_write": False,
        "memory_write": False,
        "prompt_write": False,
        "gold_label_write": False,
        "registry_write": False,
        "runtime_config_write": False,
        "service_start": False,
        "github_mutation": False,
        "broad_extraction": False,
        "backfill": False,
        "count_sample": False,
        "repo_worktree_write": repo_worktree_write,
    }
    return {
        "git_status_before": git_before,
        "git_status_after": git_after,
        "unexpected_git_status_changes": unexpected_git_changes,
        "dirty_repo_file_before": dirty_repo_before or {},
        "dirty_repo_file_after": dirty_repo_after or {},
        "dirty_repo_file_mutations": dirty_repo_file_mutations,
        "source_pdf_before": source_before,
        "source_pdf_after": source_after,
        "normal_cache_before": normal_cache_before,
        "normal_cache_after": normal_cache_after,
        "report_dir": str(report_dir),
        "report_only_durable_writes": report_only_durable_writes,
        "report_files": report_files,
        "isolated_cache_root": str(isolated_cache_root),
        "isolated_cache_contained": isolated_cache_contained,
        "isolated_cache_files": isolated_cache_files,
        "isolated_runtime_root": str(isolated_runtime_root),
        "isolated_runtime_contained": isolated_runtime_contained,
        "isolated_runtime_files": isolated_runtime_files,
        "forbidden_surface_mutation": forbidden,
        "forbidden_surface_clean": not any(forbidden.values()),
    }


def _safe_env_report(safe_env: dict[str, str]) -> dict[str, str]:
    report: dict[str, str] = {}
    for key in sorted(safe_env):
        if key not in SAFE_ENV_REPORT_KEYS:
            continue
        value = safe_env[key]
        if key in SECRET_ENV_REPORT_KEYS:
            report[key] = "<redacted>" if value else ""
        else:
            report[key] = value
    return report


def _side_effect_pass(side_effect_audit: dict[str, Any]) -> bool:
    return (
        bool(side_effect_audit.get("forbidden_surface_clean"))
        and bool(side_effect_audit.get("report_only_durable_writes"))
        and bool(side_effect_audit.get("isolated_cache_contained"))
        and bool(side_effect_audit.get("isolated_runtime_contained"))
    )


def _derive_replay_status(
    side_effect_audit: dict[str, Any],
    *,
    llm_missing: bool,
    extraction_exception_count: int,
    infrastructure_failure_count: int,
    expectation_failure_count: int,
) -> str:
    if not _side_effect_pass(side_effect_audit):
        return "FAIL"
    if llm_missing or infrastructure_failure_count:
        return "DATA_MISSING"
    if extraction_exception_count:
        return "FAIL"
    if expectation_failure_count:
        return "FAIL"
    return "PASS"


def _forbidden_surface_clean_payload() -> dict[str, bool]:
    return {
        "source_pdf_write": False,
        "normal_parser_cache_write": False,
        "db_write": False,
        "qdrant_write": False,
        "redis_write": False,
        "news_write": False,
        "memory_write": False,
        "prompt_write": False,
        "gold_label_write": False,
        "registry_write": False,
        "runtime_config_write": False,
        "service_start": False,
        "github_mutation": False,
        "broad_extraction": False,
        "backfill": False,
        "count_sample": False,
        "repo_worktree_write": False,
    }


def _write_no_run_artifacts(
    *,
    report_dir: Path,
    manifest_path: Path,
    cases: list[dict[str, Any]],
    profile: str,
    profile_info: dict[str, Any],
    llm_url: str,
    data_root: Path | None,
    safe_env: dict[str, str] | None,
    status: str,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    payload = {
        "status": status,
        "reason": reason,
        "details": details or {},
        "profile": profile,
        "profile_info": profile_info,
        "case_count": len(cases),
        "selected_case_ids": [case["case_id"] for case in cases],
        "side_effect_pass": True,
        "preflight_only": True,
        "loopback_llm_only": True,
    }
    input_manifest = {
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "selected_cases": cases,
        "profile": profile,
        "profile_info": profile_info,
        "llm_base_url": llm_url,
        "data_root": str(data_root) if data_root is not None else None,
        "safe_env": _safe_env_report(safe_env or {}),
    }
    side_effect_audit = {
        "status": status,
        "reason": reason,
        "profile": profile,
        "profile_info": profile_info,
        "report_dir": str(report_dir),
        "report_only_durable_writes": True,
        "forbidden_surface_mutation": _forbidden_surface_clean_payload(),
        "forbidden_surface_clean": True,
        "isolated_cache_contained": True,
        "isolated_runtime_contained": True,
    }
    replay_payload = {
        "artifact_type": "extraction_no_write_replay_results_v1",
        "status": status,
        "profile": profile,
        "case_count": len(cases),
        "llm_info": profile_info,
        "results": [],
        "reason": reason,
        "details": details or {},
    }
    _write_json(report_dir / "input_manifest.json", input_manifest)
    _write_json(report_dir / "replay_results.json", replay_payload)
    _write_json(report_dir / "side_effect_audit.json", side_effect_audit)
    _write_json(report_dir / "validation.json", payload)
    log_path = report_dir / "logs" / "replay.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"no_run profile={profile} status={status} reason={reason}\n")


def run_replay(args: argparse.Namespace) -> int:
    profile, profile_info, profile_preflight_issue = prepare_profile_process(args)
    manifest_path = resolve_manifest_path(Path(args.case_manifest).expanduser())
    manifest = load_manifest(manifest_path)
    cases = resolve_case_source_paths(select_cases(manifest, list(args.case)))
    report_dir = resolve_report_dir(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    _reset_report_outputs(report_dir)
    log_path = report_dir / "logs" / "replay.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")

    missing = _validate_source_files(cases)
    if missing:
        payload = {
            "status": "DATA_MISSING",
            "reason": "source files missing; refusing live fetch",
            "missing": missing,
            "profile": profile,
            "profile_info": profile_info,
        }
        _write_json(report_dir / "validation.json", payload)
        _write_json(
            report_dir / "input_manifest.json",
            {
                "manifest_path": str(manifest_path),
                "cases": cases,
                "profile": profile,
                "profile_info": profile_info,
            },
        )
        _write_json(report_dir / "replay_results.json", payload)
        _write_json(report_dir / "side_effect_audit.json", payload)
        return 2

    llm_url = assert_loopback_url(args.llm_base_url or os.environ.get("EXTRACTION_LLAMACPP_URL") or os.environ.get("LLAMACPP_URL") or "http://127.0.0.1:8001")
    git_before = _git_status()
    dirty_repo_before = _dirty_repo_file_snapshot(git_before, report_dir)
    source_before = _source_snapshot(cases)
    cache_roots = _normal_cache_roots(cases)
    normal_cache_before = _normal_cache_snapshot(cases, cache_roots)

    with tempfile.TemporaryDirectory(prefix=APPROVED_TMP_PREFIX.removeprefix("/tmp/"), dir="/tmp") as tmp_dir:
        data_root = Path(tmp_dir).resolve()
        safe_env = build_safe_env(data_root, llm_url)
        apply_safe_env(safe_env)
        if profile == DOCLING_PROFILE:
            incompatible_cases = _docling_incompatible_cases(cases)
            if incompatible_cases:
                _write_no_run_artifacts(
                    report_dir=report_dir,
                    manifest_path=manifest_path,
                    cases=cases,
                    profile=profile,
                    profile_info=profile_info,
                    llm_url=llm_url,
                    data_root=data_root,
                    safe_env=safe_env,
                    status="FAIL",
                    reason="docling_profile_incompatible_manifest_cases",
                    details={"incompatible_cases": incompatible_cases},
                )
                print(
                    json.dumps(
                        {
                            "status": "FAIL",
                            "reason": "docling_profile_incompatible_manifest_cases",
                            "report_dir": str(report_dir.relative_to(REPO_ROOT)),
                            "case_count": len(cases),
                            "side_effect_pass": True,
                            "profile": profile,
                            "preflight_only": True,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2
            if profile_preflight_issue:
                _write_no_run_artifacts(
                    report_dir=report_dir,
                    manifest_path=manifest_path,
                    cases=cases,
                    profile=profile,
                    profile_info=profile_info,
                    llm_url=llm_url,
                    data_root=data_root,
                    safe_env=safe_env,
                    status="DATA_MISSING",
                    reason=profile_preflight_issue,
                )
                print(
                    json.dumps(
                        {
                            "status": "DATA_MISSING",
                            "reason": profile_preflight_issue,
                            "report_dir": str(report_dir.relative_to(REPO_ROOT)),
                            "case_count": len(cases),
                            "side_effect_pass": True,
                            "profile": profile,
                            "preflight_only": True,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2
            docling_info, docling_issue = _verify_docling_import()
            profile_info["docling"] = docling_info
            if docling_issue:
                _write_no_run_artifacts(
                    report_dir=report_dir,
                    manifest_path=manifest_path,
                    cases=cases,
                    profile=profile,
                    profile_info=profile_info,
                    llm_url=llm_url,
                    data_root=data_root,
                    safe_env=safe_env,
                    status="DATA_MISSING",
                    reason=docling_issue,
                )
                print(
                    json.dumps(
                        {
                            "status": "DATA_MISSING",
                            "reason": docling_issue,
                            "report_dir": str(report_dir.relative_to(REPO_ROOT)),
                            "case_count": len(cases),
                            "side_effect_pass": True,
                            "profile": profile,
                            "preflight_only": True,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 2
            cases = _force_docling_profile_cases(cases)
        cache_ok, cache_root_text, cache_error, cache_verification_mode = _check_cache_root(data_root)
        input_manifest = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256(manifest_path),
            "selected_cases": cases,
            "profile": profile,
            "profile_info": profile_info,
            "llm_base_url": llm_url,
            "data_root": str(data_root),
            "cache_root": cache_root_text,
            "cache_root_isolated": cache_ok,
            "cache_root_verification_mode": cache_verification_mode,
            "safe_env": _safe_env_report(safe_env),
        }
        _write_json(report_dir / "input_manifest.json", input_manifest)
        if not cache_ok:
            validation = {"status": "FAIL", "reason": cache_error}
            _write_json(report_dir / "validation.json", validation)
            _write_json(report_dir / "replay_results.json", validation)
            _write_json(report_dir / "side_effect_audit.json", validation)
            return 2

        if args.preflight_only:
            results: list[dict[str, Any]] = []
            llm_info: dict[str, Any] = {}
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"preflight_only profile={profile} case_count={len(cases)}\n")
        else:
            try:
                results, llm_info = _run_cases(cases, llm_url, log_path)
            except Exception as exc:
                results = []
                llm_info = {
                    "status": "DATA_MISSING",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(limit=20),
                }
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"runner_exception {type(exc).__name__}: {exc}\n")

        isolated_cache_files = _list_files(Path(cache_root_text))
        isolated_runtime_files = _list_files(data_root)

    source_after = _source_snapshot(cases)
    normal_cache_after = _normal_cache_snapshot(cases, cache_roots)
    dirty_repo_after = _repo_file_snapshots(sorted(dirty_repo_before))
    git_after = _git_status()
    report_files = _report_files(report_dir)
    side_effect_audit = _surface_audit(
        git_before=git_before,
        git_after=git_after,
        source_before=source_before,
        source_after=source_after,
        normal_cache_before=normal_cache_before,
        normal_cache_after=normal_cache_after,
        dirty_repo_before=dirty_repo_before,
        dirty_repo_after=dirty_repo_after,
        report_dir=report_dir,
        report_files=report_files,
        isolated_cache_root=Path(cache_root_text),
        isolated_cache_files=isolated_cache_files,
        isolated_runtime_root=data_root,
        isolated_runtime_files=isolated_runtime_files,
    )
    extraction_exceptions = [
        row for row in results if (row.get("result") or {}).get("status") == "exception"
    ]
    infrastructure_failures = [row for row in results if _is_infrastructure_failure(row)]
    expectation_failures = _expectation_failures(results)
    llm_missing = llm_info.get("status") == "DATA_MISSING"
    side_effect_pass = _side_effect_pass(side_effect_audit)
    status = _derive_replay_status(
        side_effect_audit,
        llm_missing=llm_missing,
        extraction_exception_count=len(extraction_exceptions),
        infrastructure_failure_count=len(infrastructure_failures),
        expectation_failure_count=len(expectation_failures),
    )
    validation = {
        "status": status,
        "profile": profile,
        "profile_info": profile_info,
        "case_count": len(cases),
        "selected_case_ids": [case["case_id"] for case in cases],
        "preflight_only": bool(args.preflight_only),
        "loopback_llm_only": True,
        "llm_info": llm_info,
        "side_effect_pass": side_effect_pass,
        "extraction_exception_count": len(extraction_exceptions),
        "infrastructure_failure_count": len(infrastructure_failures),
        "expectation_failure_count": len(expectation_failures),
        "expectation_failures": expectation_failures,
    }
    replay_payload = {
        "artifact_type": "extraction_no_write_replay_results_v1",
        "status": status,
        "profile": profile,
        "case_count": len(cases),
        "llm_info": llm_info,
        "results": results,
    }
    _write_json(report_dir / "replay_results.json", replay_payload)
    _write_json(report_dir / "side_effect_audit.json", side_effect_audit)
    _write_json(report_dir / "validation.json", validation)
    side_effect_audit["report_files_after_artifact_write"] = _report_files(report_dir)
    side_effect_audit["report_files_snapshot_note"] = (
        "report_files is the safety snapshot used for status; "
        "report_files_after_artifact_write records final report-local artifacts "
        "after replay_results, validation, and side_effect_audit were written."
    )
    _write_json(report_dir / "side_effect_audit.json", side_effect_audit)
    print(
        json.dumps(
            {
                "status": status,
                "report_dir": str(report_dir.relative_to(REPO_ROOT)),
                "case_count": len(cases),
                "side_effect_pass": validation["side_effect_pass"],
                "preflight_only": bool(args.preflight_only),
                "profile": profile,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "PASS" else 2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--case", action="append", default=[], help="Certified case id/ticker/document id, or all.")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--llm-base-url", default="")
    parser.add_argument(
        "--profile",
        choices=sorted(SUPPORTED_PROFILES),
        default=BASELINE_PROFILE,
        help=(
            "Certified replay profile. baseline-no-write preserves the current minimal fallback path; "
            "docling-no-write requires an approved existing repo/backend venv with docling installed."
        ),
    )
    parser.add_argument(
        "--venv-python",
        default="",
        help=(
            "Approved existing venv Python for docling-no-write. Must be one of "
            "financial-engine_v2/.venv/bin/python, financial-engine_v2/.venv/bin/python3, "
            ".venv/bin/python, or .venv/bin/python3."
        ),
    )
    parser.add_argument("--_profile-reexeced", action="store_true", dest="_profile_reexeced", help=argparse.SUPPRESS)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate manifest, sources, env, isolated cache, and side-effect audit without calling extraction.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        return run_replay(parse_args())
    except ReplayConfigError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
