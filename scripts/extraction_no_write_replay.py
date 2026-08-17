#!/usr/bin/env python3
"""Certified no-write extraction replay runner for fixed Tenn guard cases."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
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
    REPO_ROOT
    / "financial-engine_v2"
    / "data"
    / "extraction_no_write_cases"
    / "guard_cases_v1.json"
)
CERTIFIED_MANIFEST_ROOT = (
    REPO_ROOT / "financial-engine_v2" / "data" / "extraction_no_write_cases"
)
DEFAULT_SHARED_DATA_ROOT = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data")
DEFAULT_REPORT_DIR = (
    "reports/agent_jobs/extraction_no_write_replay_harness_v1_20260618/no_write_replay"
)
APPROVED_TMP_PREFIX = "/tmp/tenn-extraction-no-write-replay-"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
BASELINE_PROFILE = "baseline-no-write"
DOCLING_PROFILE = "docling-no-write"
SUPPORTED_PROFILES = {BASELINE_PROFILE, DOCLING_PROFILE}
DEFAULT_CASE_TIMEOUT_SECONDS = 900
V2_MANIFEST_ARTIFACT_TYPE = "extraction_no_write_case_manifest_v2"
V2_MANIFEST_SHA256 = "fa1880e039ab86ae2f2d7d7ebd9444ead8fed4c362925f2105c668819898f741"
V2_CORPUS_REPO_PATH = PurePosixPath(
    "financial-engine_v2/data/broad_extraction_benchmark/v2/corpus.json"
)
V2_CORPUS_SHA256 = "815649beffc63946eeeb77771deb961e1f36f06ee5ec49c9cd6ac068a49323dd"
V2_CASE_COUNT = 20
CODE_IDENTITY_CONFLICT_EXIT_CODE = 3
V2_EXPECTED_DEPENDENCY_VERSIONS = {
    "httpx": "0.27.2",
    "fastapi": "0.115.6",
    "pydantic": "2.9.2",
    "SQLAlchemy": "2.0.36",
    "celery": "5.4.0",
    "redis": "5.1.1",
    "PyMuPDF": "1.24.10",
}
V2_LAUNCH_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONHASHSEED",
    "PYTHONNOUSERSITE",
    "PYTHONSAFEPATH",
}
CODE_IDENTITY_PATHS = (
    "scripts/run_broad_extraction_benchmark_v2.py",
    "scripts/extraction_no_write_replay.py",
    "financial-engine_v2/backend/app/services/broad_extraction_benchmark.py",
    "financial-engine_v2/backend/app/services/multipass_extraction.py",
    "financial-engine_v2/backend/app/services/financial_metric_contract.py",
)
TRANSPORT_EXCEPTION_TYPES = frozenset(
    {
        "closeerror",
        "connectionerror",
        "connecterror",
        "connecttimeout",
        "localprotocolerror",
        "networkerror",
        "pooltimeout",
        "protocolerror",
        "proxyerror",
        "readerror",
        "readtimeout",
        "remoteprotocolerror",
        "timeoutexception",
        "transporterror",
        "unsupportedprotocol",
        "writeerror",
        "writetimeout",
    }
)
RAW_TRANSPORT_EXCEPTION_TYPES = TRANSPORT_EXCEPTION_TYPES | {"httperror"}
CAPTURED_TRANSPORT_EXCEPTION_TYPES = TRANSPORT_EXCEPTION_TYPES | {
    "llamacppserverunavailable"
}
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


class CodeIdentityConflict(ReplayConfigError):
    """Raised when v2 execution code no longer matches its invocation receipt."""


class CaseTimeoutError(TimeoutError):
    """Raised when one replay case exceeds the configured runtime budget."""


@contextmanager
def _case_timeout(seconds: int):
    if seconds <= 0:
        yield
        return

    def _raise_timeout(_signum: int, _frame: Any) -> None:
        raise CaseTimeoutError(f"case_timeout: exceeded {seconds} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


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
        raise ReplayConfigError(
            f"path must be repo-relative without parent segments: {path_text}"
        )
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
        raise ReplayConfigError(
            "resolved report dir escaped reports/agent_jobs"
        ) from exc
    for parent in (repo_root / "reports", allowed_root, allowed_root / path.parts[2]):
        if parent.exists() and parent.is_symlink():
            raise ReplayConfigError(
                f"report path parent must not be symlinked: {parent}"
            )
    return resolved


def resolve_manifest_path(path: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    raw_path = Path(path)
    resolved = (
        (repo_root / raw_path).resolve()
        if not raw_path.is_absolute()
        else raw_path.resolve()
    )
    certified_root = CERTIFIED_MANIFEST_ROOT.resolve()
    try:
        resolved.relative_to(certified_root)
    except ValueError as exc:
        if (
            resolved.is_symlink()
            or not resolved.is_file()
            or _sha256(resolved) != V2_MANIFEST_SHA256
        ):
            raise ReplayConfigError(
                f"case manifest must be under certified manifest root: {certified_root}; "
                "only the exact hash-bound v2 manifest may be external"
            ) from exc
    if resolved.exists() and resolved.is_symlink():
        raise ReplayConfigError(f"case manifest must not be a symlink: {resolved}")
    return resolved


def load_manifest(path: Path, *, v2_corpus_path: Path | None = None) -> dict[str, Any]:
    manifest = _read_json(path)
    artifact_type = manifest.get("artifact_type")
    if artifact_type not in {
        "extraction_no_write_case_manifest_v1",
        V2_MANIFEST_ARTIFACT_TYPE,
    }:
        raise ReplayConfigError(
            "manifest artifact_type must be extraction_no_write_case_manifest_v1 "
            f"or {V2_MANIFEST_ARTIFACT_TYPE}"
        )
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
            raise ReplayConfigError(
                f"case[{index}] missing fields: {', '.join(missing)}"
            )
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
    if artifact_type == V2_MANIFEST_ARTIFACT_TYPE:
        _validate_v2_manifest_contract(path, manifest, corpus_path=v2_corpus_path)
    return manifest


def _validate_v2_manifest_contract(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    corpus_path: Path | None = None,
) -> dict[str, Any]:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ReplayConfigError("v2 case manifest must be a non-symlink regular file")
    observed_manifest_sha = _sha256(manifest_path)
    if observed_manifest_sha != V2_MANIFEST_SHA256:
        raise ReplayConfigError(
            f"v2 case manifest SHA-256 mismatch: expected {V2_MANIFEST_SHA256}, "
            f"observed {observed_manifest_sha}"
        )
    cases = manifest["cases"]
    if len(cases) != V2_CASE_COUNT:
        raise ReplayConfigError(
            f"v2 case manifest must contain exactly {V2_CASE_COUNT} cases"
        )
    certification = manifest["certification"]
    if certification.get("source_contract") != V2_CORPUS_REPO_PATH.as_posix():
        raise ReplayConfigError(
            "v2 case manifest must declare the exact v2 corpus path"
        )
    corpus_path = (
        corpus_path.expanduser().resolve()
        if corpus_path is not None
        else repo_root.joinpath(*V2_CORPUS_REPO_PATH.parts)
    )
    if corpus_path.is_symlink() or not corpus_path.is_file():
        raise ReplayConfigError(
            f"v2 corpus must be a non-symlink regular file: {corpus_path}"
        )
    observed_corpus_sha = _sha256(corpus_path)
    if observed_corpus_sha != V2_CORPUS_SHA256:
        raise ReplayConfigError(
            f"v2 corpus SHA-256 mismatch: expected {V2_CORPUS_SHA256}, "
            f"observed {observed_corpus_sha}"
        )
    corpus = _read_json(corpus_path)
    if corpus.get("artifact_type") != "broad_extraction_benchmark_corpus_v2":
        raise ReplayConfigError("v2 corpus artifact_type mismatch")
    documents = corpus.get("documents")
    if not isinstance(documents, list) or len(documents) != V2_CASE_COUNT:
        raise ReplayConfigError(
            f"v2 corpus must contain exactly {V2_CASE_COUNT} documents"
        )
    document_by_id = {
        row.get("document_id"): row for row in documents if isinstance(row, dict)
    }
    if len(document_by_id) != len(documents):
        raise ReplayConfigError("v2 corpus document IDs must be unique")
    seen_documents: set[str] = set()
    for case in cases:
        document_id = str(case.get("document_id") or "")
        document = document_by_id.get(document_id)
        if document is None or document_id in seen_documents:
            raise ReplayConfigError("v2 cases must map one-to-one to corpus documents")
        if (
            case.get("ticker") != document.get("issuer_id")
            or case.get("source_path") != document.get("source_path")
            or document.get("admission_status") != "admitted"
        ):
            raise ReplayConfigError(
                f"v2 case/corpus identity mismatch: {case.get('case_id')}"
            )
        seen_documents.add(document_id)
    if seen_documents != set(document_by_id):
        raise ReplayConfigError("v2 case manifest omits corpus documents")
    return {
        "manifest_sha256": observed_manifest_sha,
        "corpus_path": str(corpus_path),
        "corpus_sha256": observed_corpus_sha,
        "document_by_id": document_by_id,
    }


def select_cases(
    manifest: dict[str, Any], selectors: list[str]
) -> list[dict[str, Any]]:
    cases = manifest["cases"]
    if manifest.get("artifact_type") == V2_MANIFEST_ARTIFACT_TYPE and selectors not in (
        [],
        ["all"],
    ):
        raise ReplayConfigError("v2 replay requires the complete 20-case manifest")
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
    candidates.extend(
        data_root / "asx" / "docs" for data_root in _candidate_data_roots()
    )
    return _unique_paths(candidates)


def _portable_source_suffixes(
    path_text: str,
) -> tuple[PurePosixPath | None, PurePosixPath | None]:
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
        candidates.extend(
            data_root / data_suffix for data_root in _candidate_data_roots()
        )
    if docs_suffix is not None:
        candidates.extend(
            docs_root / docs_suffix for docs_root in _candidate_docs_roots()
        )
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
        resolved_case["source_path_candidates"] = [
            str(candidate) for candidate in candidates
        ]
        resolved_cases.append(resolved_case)
    return resolved_cases


def resolve_v2_case_source_paths(
    manifest_path: Path,
    manifest: dict[str, Any],
    *,
    source_root: Path,
    repo_root: Path = REPO_ROOT,
    corpus_path: Path | None = None,
) -> list[dict[str, Any]]:
    contract = _validate_v2_manifest_contract(
        manifest_path,
        manifest,
        repo_root=repo_root,
        corpus_path=corpus_path,
    )
    document_by_id = contract["document_by_id"]
    resolved_cases: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        document = document_by_id[str(case["document_id"])]
        declared = Path(str(case["source_path"])).expanduser()
        if declared.is_absolute():
            source = declared
        else:
            relative = _normalize_repo_path(str(case["source_path"]))
            source = source_root.joinpath(*relative.parts)
        if source.is_symlink() or not source.is_file():
            raise ReplayConfigError(
                f"v2 declared source missing or not a regular file: {case['case_id']}:{source}"
            )
        observed = _sha256(source)
        expected = document.get("source_sha256")
        if observed != expected:
            raise ReplayConfigError(
                f"v2 source SHA-256 mismatch for {case['case_id']}: "
                f"expected {expected}, observed {observed}"
            )
        resolved = dict(case)
        resolved["source_path"] = str(source)
        resolved["source_path_declared"] = str(case["source_path"])
        resolved["source_sha256"] = observed
        resolved_cases.append(resolved)
    return resolved_cases


def _materialize_v2_execution_sources(
    cases: list[dict[str, Any]], isolated_root: Path
) -> list[dict[str, Any]]:
    isolated_root.mkdir(parents=True, exist_ok=False)
    materialized: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        source = Path(str(case["source_path"]))
        suffix = source.suffix.lower() or ".bin"
        target = isolated_root / f"{index:02d}-{case['case_id']}{suffix}"
        digest = hashlib.sha256()
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            source_fd = os.open(source, flags)
        except OSError as exc:
            raise ReplayConfigError(
                f"unable to open v2 source for isolated binding: {case['case_id']}:{source}"
            ) from exc
        try:
            if not stat.S_ISREG(os.fstat(source_fd).st_mode):
                raise ReplayConfigError(
                    f"v2 source is not a regular file: {case['case_id']}:{source}"
                )
            with os.fdopen(source_fd, "rb", closefd=False) as source_handle:
                with target.open("xb") as target_handle:
                    for chunk in iter(lambda: source_handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                        target_handle.write(chunk)
        finally:
            os.close(source_fd)
        observed = digest.hexdigest()
        expected = str(case.get("source_sha256") or "")
        if observed != expected:
            raise ReplayConfigError(
                f"v2 isolated source SHA-256 mismatch for {case['case_id']}: "
                f"expected {expected}, observed {observed}"
            )
        target.chmod(0o400)
        resolved = dict(case)
        resolved["source_path_original"] = str(source)
        resolved["source_path"] = str(target)
        resolved["source_sha256"] = observed
        materialized.append(resolved)
    return materialized


def validate_v2_invocation_receipt(
    receipt_path: Path,
    *,
    manifest_path: Path,
    corpus_path: Path,
    report_dir: Path,
    source_root: Path,
    llm_url: str,
    case_timeout_seconds: int,
    profile: str,
    requested_git_head: str | None = None,
) -> dict[str, Any]:
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ReplayConfigError(
            "v2 launch requires an existing non-symlink invocation receipt"
        )
    receipt_path = receipt_path.resolve()
    manifest_path = manifest_path.resolve()
    corpus_path = corpus_path.resolve()
    report_dir = report_dir.resolve()
    receipt = _read_json(receipt_path)
    if receipt.get("artifact_type") != "broad_extraction_invocation_receipt_v2":
        raise ReplayConfigError("v2 invocation receipt artifact_type mismatch")
    invocation_id = str(receipt.get("invocation_id") or "")
    try:
        bound_receipt = Path(str(receipt["receipt_path"])).resolve()
        final_output_path = Path(str(receipt["final_output_root"]))
        staging_root_path = Path(str(receipt["staging_root"]))
        final_output = final_output_path.resolve()
        staging_root = staging_root_path.resolve()
        replay_report_dir = Path(str(receipt["replay_report_dir"])).resolve()
        bound_manifest = Path(str(receipt["case_manifest_path"])).resolve()
        bound_corpus = Path(str(receipt["corpus_path"])).resolve()
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ReplayConfigError(
            "v2 invocation receipt path bindings are invalid"
        ) from exc
    expected_receipt = final_output.parent / "INVOCATION_RECEIPT.json"
    expected_stage = (
        final_output.parent / f".{final_output.name}.staging-{invocation_id}"
    )
    if (
        not invocation_id
        or bound_receipt != receipt_path
        or expected_receipt != receipt_path
        or staging_root != expected_stage
        or replay_report_dir != staging_root / "replay"
        or replay_report_dir != report_dir
        or bound_manifest != manifest_path
        or bound_corpus != corpus_path
    ):
        raise ReplayConfigError(
            "v2 invocation receipt output/report/input path binding mismatch"
        )
    if final_output_path.exists() or final_output_path.is_symlink():
        raise ReplayConfigError(
            f"v2 invocation receipt final output already exists: {final_output}"
        )
    if staging_root_path.exists() or staging_root_path.is_symlink():
        raise ReplayConfigError(
            f"v2 invocation receipt staging root already exists: {staging_root}"
        )
    if receipt.get("case_manifest_sha256") != _sha256(manifest_path):
        raise ReplayConfigError("v2 invocation receipt manifest SHA-256 mismatch")
    if receipt.get("corpus_sha256") != V2_CORPUS_SHA256:
        raise ReplayConfigError("v2 invocation receipt corpus SHA-256 mismatch")
    if receipt.get("case_count") != V2_CASE_COUNT:
        raise ReplayConfigError("v2 invocation receipt case count mismatch")
    validate_v2_launch_environment(receipt.get("launch_environment"))
    validate_v2_running_interpreter(receipt.get("interpreter"))
    code_identity = receipt.get("code_identity")
    if not isinstance(code_identity, dict):
        raise ReplayConfigError("v2 invocation receipt code identity is invalid")
    expected_git_head = str(code_identity.get("head_sha") or "")
    if (
        requested_git_head is not None
        and str(requested_git_head).strip() != expected_git_head
    ):
        raise ReplayConfigError("v2 invocation receipt Git HEAD argument mismatch")
    require_v2_code_identity(code_identity)
    command = receipt.get("command")
    if not isinstance(command, list) or not all(
        isinstance(item, str) for item in command
    ):
        raise ReplayConfigError("v2 invocation receipt command binding is invalid")

    def command_option(name: str) -> str:
        if command.count(name) != 1:
            raise ReplayConfigError(
                f"v2 invocation receipt command must bind {name} once"
            )
        index = command.index(name)
        if index + 1 >= len(command):
            raise ReplayConfigError(f"v2 invocation receipt command omits {name} value")
        return command[index + 1]

    if (
        len(command) < 5
        or not _same_python_path(Path(command[0]), Path(sys.executable))
        or command[1] != "-I"
        or command[2] != "-B"
        or command[3] != "-S"
        or Path(command[4]).resolve() != Path(__file__).resolve()
        or Path(command_option("--case-manifest")).resolve() != manifest_path
        or Path(command_option("--source-contract")).resolve() != corpus_path
        or resolve_report_dir(command_option("--report-dir")) != report_dir
        or Path(command_option("--invocation-receipt")).resolve() != receipt_path
        or Path(command_option("--source-root")).resolve() != source_root.resolve()
        or assert_loopback_url(command_option("--llm-base-url")) != llm_url
        or command_option("--case-timeout-seconds") != str(case_timeout_seconds)
        or command_option("--expected-git-head") != expected_git_head
        or profile != BASELINE_PROFILE
        or command_option("--profile") != profile
        or command_option("--case") != "all"
    ):
        raise ReplayConfigError("v2 invocation receipt command binding mismatch")
    return receipt


def validate_v2_launch_environment(bound_environment: Any) -> None:
    if not isinstance(bound_environment, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in bound_environment.items()
    ):
        raise ReplayConfigError("v2 invocation receipt launch environment is invalid")
    if set(bound_environment) - V2_LAUNCH_ENV_KEYS:
        raise ReplayConfigError(
            "v2 invocation receipt launch environment has unsafe keys"
        )
    for key, value in {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }.items():
        if bound_environment.get(key) != value:
            raise ReplayConfigError(
                f"v2 invocation receipt launch environment must bind {key}={value}"
            )
    if dict(os.environ) != bound_environment:
        raise ReplayConfigError("v2 invocation receipt launch environment mismatch")


def validate_v2_running_interpreter(binding: Any) -> None:
    if not isinstance(binding, dict):
        raise ReplayConfigError("v2 invocation receipt interpreter binding is invalid")
    expected_binary_sha = str(binding.get("binary_sha256") or "")
    observed_binary_sha = _sha256(Path(sys.executable).resolve())
    if (
        re.fullmatch(r"[0-9a-f]{64}", expected_binary_sha) is None
        or observed_binary_sha != expected_binary_sha
    ):
        raise ReplayConfigError(
            "v2 invocation receipt running interpreter SHA-256 mismatch"
        )
    site_packages = binding.get("site_packages")
    if not isinstance(site_packages, list) or not site_packages:
        raise ReplayConfigError(
            "v2 invocation receipt interpreter site-package binding is invalid"
        )
    for raw_path in site_packages:
        site_path = Path(str(raw_path))
        if (
            not site_path.is_absolute()
            or site_path.is_symlink()
            or not site_path.is_dir()
        ):
            raise ReplayConfigError(
                "v2 invocation receipt interpreter site-package path is invalid"
            )
        site_text = str(site_path)
        if site_text not in sys.path:
            sys.path.append(site_text)
    expected_versions = binding.get("versions")
    if expected_versions != V2_EXPECTED_DEPENDENCY_VERSIONS:
        raise ReplayConfigError(
            "v2 invocation receipt interpreter dependency binding mismatch"
        )
    observed_versions = {
        name: importlib.metadata.version(name)
        for name in V2_EXPECTED_DEPENDENCY_VERSIONS
    }
    if observed_versions != expected_versions:
        raise ReplayConfigError(
            "v2 invocation receipt running dependency versions mismatch"
        )
    observed_snapshot_sha = hashlib.sha256(
        json.dumps(observed_versions, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if binding.get("dependency_snapshot_sha256") != observed_snapshot_sha:
        raise ReplayConfigError(
            "v2 invocation receipt dependency snapshot SHA-256 mismatch"
        )


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
    return [
        _abspath_no_symlink(REPO_ROOT / relative_path)
        for relative_path in APPROVED_VENV_RELATIVE_PYTHONS
    ]


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


def _select_docling_venv_python(
    requested_venv_python: str,
) -> tuple[Path | None, dict[str, Any]]:
    info: dict[str, Any] = {
        "approved_candidates": [
            str(candidate) for candidate in approved_venv_candidates()
        ],
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
            info["current_python_is_selected"] = _same_python_path(
                current_python, candidate
            )
            info["selected_exists"] = True
            info["selected_executable"] = True
            return candidate, info
    info["selected_venv_python"] = None
    info["current_python_is_selected"] = False
    info["selected_exists"] = False
    info["selected_executable"] = False
    return None, info


def _reexec_for_docling_profile(
    selected_python: Path, args: argparse.Namespace
) -> None:
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


def prepare_profile_process(
    args: argparse.Namespace,
) -> tuple[str, dict[str, Any], str | None]:
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
        return (
            profile,
            profile_info,
            f"approved_docling_venv_python_missing:{selected_python}",
        )
    if not os.access(selected_python, os.X_OK):
        return (
            profile,
            profile_info,
            f"approved_docling_venv_python_not_executable:{selected_python}",
        )
    if not _same_python_path(Path(sys.executable), selected_python):
        if args._profile_reexeced:
            return (
                profile,
                profile_info,
                f"docling_profile_reexec_failed:{selected_python}",
            )
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


def _dirty_repo_file_snapshot(
    git_rows: list[str], report_dir: Path
) -> dict[str, dict[str, Any]]:
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


def _git_code_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReplayConfigError(f"Git code-identity validation failed: {detail}")
    return completed.stdout.strip()


def inspect_code_identity(expected_head: str) -> dict[str, Any]:
    expected = str(expected_head or "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise ReplayConfigError("v2 invocation receipt Git HEAD is invalid")
    observed = _git_code_output("rev-parse", "HEAD")
    if observed != expected:
        raise ReplayConfigError(
            f"v2 invocation receipt Git HEAD mismatch: expected {expected}, observed {observed}"
        )
    tracked_status = _git_code_output(
        "status", "--porcelain=v1", "--untracked-files=no"
    )
    if tracked_status:
        raise ReplayConfigError(
            f"v2 invocation receipt tracked worktree is not clean: {tracked_status}"
        )
    code_status = _git_code_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        "scripts",
        "financial-engine_v2/backend",
    )
    if code_status:
        raise ReplayConfigError(
            f"v2 invocation receipt code paths are not clean: {code_status}"
        )
    tree_sha = _git_code_output("show", "-s", "--format=%T", "HEAD")
    file_hashes: dict[str, str] = {}
    for relative in CODE_IDENTITY_PATHS:
        digest = _sha256(REPO_ROOT / relative)
        if digest is None:
            raise ReplayConfigError(
                f"v2 invocation receipt code identity source missing: {relative}"
            )
        file_hashes[relative] = digest
    return {
        "head_sha": observed,
        "tree_sha": tree_sha,
        "tracked_files_sha256": file_hashes,
    }


def require_v2_code_identity(binding: Any) -> None:
    if not isinstance(binding, dict):
        raise CodeIdentityConflict("v2 invocation receipt code identity is invalid")
    expected_head = str(binding.get("head_sha") or "")
    try:
        observed = inspect_code_identity(expected_head)
    except (OSError, ReplayConfigError) as exc:
        raise CodeIdentityConflict(
            f"v2 invocation receipt code identity conflict: {exc}"
        ) from exc
    if observed != binding:
        raise CodeIdentityConflict("v2 invocation receipt code identity mismatch")


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
    snapshots: dict[str, dict[str, Any]] = {}
    for case in cases:
        source_path = Path(str(case["source_path"]))
        source_dir = source_path.parent
        snapshots[str(case["case_id"])] = {
            "source_file": _file_snapshot(source_path, hash_file=True),
            "source_dir": str(source_dir),
            "source_dir_files": _list_files(source_dir, hash_files=True),
        }
    return snapshots


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
        (
            REPO_ROOT
            / "financial-engine_v2"
            / "data"
            / "reports"
            / "extraction_cache"
            / "docling_extract"
        ).resolve()
    }
    for case in cases:
        data_root = _data_root_from_source(str(case["source_path"]))
        if data_root is not None:
            roots.add(
                (
                    data_root / "reports" / "extraction_cache" / "docling_extract"
                ).resolve()
            )
    return sorted(roots)


def _normal_cache_snapshot(
    cases: list[dict[str, Any]], roots: list[Path]
) -> dict[str, Any]:
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
            raise ReplayConfigError(
                f"report output escaped report dir: {relative_path}"
            ) from exc
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
            "MARKETINDEX_ANNOUNCEMENTS_FILE": str(
                data_root / "raw" / "marketindex_announcements.json"
            ),
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
            "TENN_EXTRACTION_ACTIVE_FILE": str(
                data_root / "runtime" / "extraction_active.json"
            ),
            "MODEL_ROUTING_CONFIG": str(
                REPO_ROOT
                / "financial-engine_v2"
                / "backend"
                / "app"
                / "config"
                / "model_routing.yaml"
            ),
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
    for key in (
        "HOME",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_STATE_HOME",
    ):
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
    api_key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or "local-openai-key"
    )
    client = httpx.Client(
        base_url=base_url, timeout=180.0, headers={"Authorization": f"Bearer {api_key}"}
    )
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


def _benchmark_internal_metrics(
    multipass_module: Any, debug_capture: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {
        "values": {},
        "metric_source_scales": {},
        "metric_scale_sources": {},
        "provenance": {},
        "source_cells": {},
    }
    pass3a_results = debug_capture.get("pass3a_results")
    if not isinstance(pass3a_results, list):
        return observations
    for candidate in pass3a_results:
        if (
            not isinstance(candidate, dict)
            or candidate.get("_source") != "balance_sheet"
        ):
            continue
        value = candidate.get("total_debt")
        row_refs = candidate.get("row_refs")
        row_ref = row_refs.get("total_debt") if isinstance(row_refs, dict) else None
        period_source_cells = candidate.get("_period_source_cells")
        source_cell = (
            period_source_cells.get("total_debt")
            if isinstance(period_source_cells, dict)
            else None
        )
        if (
            not isinstance(source_cell, dict)
            or not source_cell.get("raw_value")
            or not source_cell.get("requested_period_end")
            or source_cell.get("scaled_value") != value
        ):
            continue
        if not multipass_module._is_strong_total_debt_evidence(row_ref, value):
            continue
        observations["values"]["total_debt"] = value
        scale = str(candidate.get("_scale") or "").strip()
        if scale and scale != "unknown":
            observations["metric_source_scales"]["total_debt"] = scale
            observations["metric_scale_sources"]["total_debt"] = str(
                candidate.get("_scale_source") or "unknown"
            )
        page = candidate.get("_page_number")
        page_tag = f"page_{page}" if page is not None else "page_?"
        observations["provenance"]["total_debt"] = f"balance_sheet:{page_tag}:{row_ref}"
        observations["source_cells"]["total_debt"] = dict(source_cell)
        break
    return observations


def _compact_payload(
    result: Any,
    *,
    benchmark_internal_metrics: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = result.payload or {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    compacted = {
        "status": result.status,
        "error": result.error,
        "period_type": payload.get("period_type"),
        "period_start": payload.get("period_start"),
        "period_end": payload.get("period_end"),
        "scale": payload.get("scale"),
        "currency": payload.get("currency"),
        "confidence_metrics": payload.get("confidence_metrics"),
        "non_null_metric_count": len(
            [value for value in metrics.values() if value is not None]
        ),
        "non_null_metrics": {
            key: value for key, value in metrics.items() if value is not None
        },
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
    if benchmark_internal_metrics is not None:
        field_provenance = payload.get("field_provenance")
        metric_source_cells = {
            str(metric): dict(source_cell)
            for metric, provenance in (
                field_provenance.items() if isinstance(field_provenance, dict) else ()
            )
            if isinstance(provenance, dict)
            and isinstance((source_cell := provenance.get("source_cell")), dict)
        }
        compacted.update(
            {
                "benchmark_metric_source_cells": metric_source_cells,
                "benchmark_internal_metrics": benchmark_internal_metrics.get(
                    "values", {}
                ),
                "benchmark_internal_metric_source_scales": benchmark_internal_metrics.get(
                    "metric_source_scales", {}
                ),
                "benchmark_internal_metric_scale_sources": benchmark_internal_metrics.get(
                    "metric_scale_sources", {}
                ),
                "benchmark_internal_provenance": benchmark_internal_metrics.get(
                    "provenance", {}
                ),
                "benchmark_internal_source_cells": benchmark_internal_metrics.get(
                    "source_cells", {}
                ),
            }
        )
    return compacted


def _case_metadata(case: dict[str, Any]) -> dict[str, str]:
    return {
        "document_id": str(case["document_id"]),
        "ticker": str(case["ticker"]),
        "title": str(case["title"]),
    }


def _attach_v2_failure_capture(
    row: dict[str, Any],
    debug_capture: dict[str, Any],
    *,
    enabled: bool,
) -> None:
    if enabled:
        row["pass3a_failures"] = debug_capture.get("pass3a_failures", [])
        pass1_failure_chain = debug_capture.get("pass1_failure_chain")
        if isinstance(pass1_failure_chain, list):
            row["pass1_failure_chain"] = pass1_failure_chain


def _run_cases(
    cases: list[dict[str, Any]],
    llm_url: str,
    log_path: Path,
    *,
    case_timeout_seconds: int,
    include_benchmark_internal_metrics: bool = False,
    expected_code_identity: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if expected_code_identity is not None:
        require_v2_code_identity(expected_code_identity)
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.services import llm as llm_module
    from app.services import multipass_extraction as mp

    if expected_code_identity is not None:
        require_v2_code_identity(expected_code_identity)
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
                log.write(
                    f"case_start {case_id} timeout_seconds={case_timeout_seconds}\n"
                )
                try:
                    with _case_timeout(case_timeout_seconds):
                        result = mp.run_multipass_extraction(
                            str(case["source_path"]),
                            _case_metadata(case),
                            client,
                            skip_narrative=bool(case.get("skip_narrative", True)),
                            parser_backend=str(case.get("parser_backend") or "docling"),
                            strict_parser=bool(case.get("strict_parser", False)),
                            observer=observer,
                            debug_capture=debug_capture,
                            capture_pass1_failures=include_benchmark_internal_metrics,
                            capture_pass3a_failures=include_benchmark_internal_metrics,
                            capture_benchmark_source_cells=(
                                include_benchmark_internal_metrics
                            ),
                            openability_pages=case.get("openability_pages"),
                            openability_selected_tables=bool(
                                case.get("openability_selected_tables", False)
                            ),
                        )
                    payload = _compact_payload(
                        result,
                        benchmark_internal_metrics=(
                            _benchmark_internal_metrics(mp, debug_capture)
                            if include_benchmark_internal_metrics
                            else None
                        ),
                    )
                    case_result = {
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
                        "pass3a_result_count": len(
                            debug_capture.get("pass3a_results") or []
                        ),
                        "case_timeout_seconds": case_timeout_seconds,
                        "result": payload,
                    }
                    _attach_v2_failure_capture(
                        case_result,
                        debug_capture,
                        enabled=include_benchmark_internal_metrics,
                    )
                    results.append(case_result)
                    log.write(
                        f"case_done {case_id} status={result.status} error={result.error}\n"
                    )
                except Exception as exc:  # pragma: no cover - exercised by smoke runs
                    exception_result = {
                        "case_id": case_id,
                        "role": case.get("role"),
                        "ticker": case.get("ticker"),
                        "document_id": case.get("document_id"),
                        "source_path": case.get("source_path"),
                        "elapsed_s": round(time.monotonic() - started, 3),
                        "observer_events": observer.events,
                        "case_timeout_seconds": case_timeout_seconds,
                        "result": {
                            "status": "exception",
                            "error": f"{type(exc).__name__}: {exc}",
                            "traceback": traceback.format_exc(limit=20),
                        },
                    }
                    _attach_v2_failure_capture(
                        exception_result,
                        debug_capture,
                        enabled=include_benchmark_internal_metrics,
                    )
                    results.append(exception_result)
                    log.write(f"case_exception {case_id} {type(exc).__name__}: {exc}\n")
        finally:
            if client is not None:
                client.close()
    if expected_code_identity is not None:
        require_v2_code_identity(expected_code_identity)
    return results, llm_info


def _is_infrastructure_failure(
    row: dict[str, Any], *, include_raw_transport: bool = False
) -> bool:
    if include_raw_transport and (
        _has_captured_infrastructure_failure(row.get("pass1_failure_chain"))
        or _has_pass3a_infrastructure_failure(row)
    ):
        return True
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    error = str(result.get("error") or "").lower()
    if not error:
        return False
    if "case_timeout:" in error:
        return True
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
    if include_raw_transport and result.get("status") == "exception":
        exception_type = error.partition(":")[0].strip()
        if (
            exception_type in RAW_TRANSPORT_EXCEPTION_TYPES
            or exception_type == "modulenotfounderror"
        ):
            return True
    return error.startswith(("pass1:", "pass3a:", "pass3b:")) and any(
        marker in error for marker in markers
    )


def _has_pass3a_infrastructure_failure(row: dict[str, Any]) -> bool:
    failures = row.get("pass3a_failures")
    if not isinstance(failures, list):
        return False
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        for key in ("initial_error_chain", "retry_error_chain"):
            chain = failure.get(key)
            if _has_captured_infrastructure_failure(chain):
                return True
    return False


def _has_captured_infrastructure_failure(chain: Any) -> bool:
    if not isinstance(chain, list):
        return False
    for cause in chain:
        if not isinstance(cause, dict):
            continue
        exception_type = str(cause.get("exception_type") or "").lower()
        status_code = cause.get("status_code")
        if exception_type in CAPTURED_TRANSPORT_EXCEPTION_TYPES:
            return True
        if isinstance(status_code, int) and status_code >= 500:
            return True
    return False


def _is_runner_infrastructure_exception(exc: Exception) -> bool:
    if isinstance(exc, ModuleNotFoundError):
        return True
    exception_type = type(exc).__name__.lower()
    if any(
        marker in exception_type
        for marker in ("connect", "connection", "timeout", "http")
    ):
        return True
    error = f"{type(exc).__name__}: {exc}".lower()
    markers = (
        "no module named",
        "server_unavailable",
        "http_",
        "llamacpp",
        "ollama_url",
        "llamacpp_url",
    )
    return any(marker in error for marker in markers)


def _runner_exception_payload(
    exc: Exception,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    error = f"{type(exc).__name__}: {exc}"
    traceback_text = traceback.format_exc(limit=20)
    if _is_runner_infrastructure_exception(exc):
        return [], {
            "status": "DATA_MISSING",
            "classification": "infrastructure",
            "error": error,
            "traceback": traceback_text,
        }
    return [
        {
            "case_id": "__runner__",
            "role": "runner_exception",
            "result": {
                "status": "exception",
                "error": error,
                "traceback": traceback_text,
            },
        }
    ], {
        "status": "exception",
        "classification": "unexpected_runner_exception",
        "error": error,
        "traceback": traceback_text,
    }


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
            mismatches["status"] = {
                "expected": expected_status,
                "observed": observed_status,
            }
        if expected_period_type and observed_period_type != expected_period_type:
            mismatches["period_type"] = {
                "expected": expected_period_type,
                "observed": observed_period_type,
            }
        if expected_period_end and observed_period_end != expected_period_end:
            mismatches["period_end"] = {
                "expected": expected_period_end,
                "observed": observed_period_end,
            }
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
            data_root / "reports" / "extraction_cache" / "docling_extract"
        ).resolve()
    try:
        cache_root.relative_to(data_root)
    except ValueError:
        return (
            False,
            str(cache_root),
            f"cache root is outside isolated DATA_ROOT: {cache_root}",
            verification_mode,
        )
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
    code_identity_conflict: str | None = None,
) -> dict[str, Any]:
    source_tree_write = source_before != source_after
    normal_parser_cache_write = normal_cache_before != normal_cache_after
    unexpected_git_changes = _unexpected_git_status_changes(
        git_before, git_after, report_dir
    )
    dirty_repo_file_mutations = (
        dirty_repo_before if dirty_repo_before is not None else {}
    ) != (dirty_repo_after if dirty_repo_after is not None else {})
    repo_worktree_write = (
        bool(unexpected_git_changes)
        or dirty_repo_file_mutations
        or code_identity_conflict is not None
    )
    allowed_report_prefix = str(report_dir) + os.sep
    report_only_durable_writes = all(
        str(row.get("path", "")).startswith(allowed_report_prefix)
        for row in report_files
    )
    isolated_prefix = str(isolated_cache_root) + os.sep
    isolated_cache_contained = all(
        str(row.get("path", "")).startswith(isolated_prefix)
        for row in isolated_cache_files
    )
    isolated_runtime_prefix = str(isolated_runtime_root) + os.sep
    isolated_runtime_contained = all(
        str(row.get("path", "")).startswith(isolated_runtime_prefix)
        for row in isolated_runtime_files
    )
    forbidden = {
        "source_pdf_write": source_tree_write,
        "source_tree_write": source_tree_write,
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
        "code_identity_conflict": code_identity_conflict,
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
        "source_tree_write": False,
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
    raw_source_contract = str(getattr(args, "source_contract", "") or "").strip()
    source_contract_path = (
        Path(raw_source_contract).expanduser() if raw_source_contract else None
    )
    manifest = load_manifest(manifest_path, v2_corpus_path=source_contract_path)
    selected_cases = select_cases(manifest, list(args.case))
    is_v2 = manifest.get("artifact_type") == V2_MANIFEST_ARTIFACT_TYPE
    llm_url = assert_loopback_url(
        args.llm_base_url
        or os.environ.get("EXTRACTION_LLAMACPP_URL")
        or os.environ.get("LLAMACPP_URL")
        or "http://127.0.0.1:8001"
    )
    report_dir = resolve_report_dir(args.report_dir)
    receipt: dict[str, Any] | None = None
    code_identity_conflict: str | None = None
    if is_v2:
        cases = resolve_v2_case_source_paths(
            manifest_path,
            manifest,
            source_root=Path(
                getattr(args, "source_root", DEFAULT_SHARED_DATA_ROOT)
            ).expanduser(),
            corpus_path=source_contract_path,
        )
        if not args.preflight_only:
            raw_receipt = str(getattr(args, "invocation_receipt", "") or "").strip()
            if not raw_receipt:
                raise ReplayConfigError("v2 launch requires --invocation-receipt")
            if source_contract_path is None:
                raise ReplayConfigError("v2 launch requires --source-contract")
            receipt = validate_v2_invocation_receipt(
                Path(raw_receipt).expanduser(),
                manifest_path=manifest_path,
                corpus_path=source_contract_path,
                report_dir=report_dir,
                source_root=Path(
                    getattr(args, "source_root", DEFAULT_SHARED_DATA_ROOT)
                ).expanduser(),
                llm_url=llm_url,
                case_timeout_seconds=int(args.case_timeout_seconds),
                profile=profile,
                requested_git_head=str(getattr(args, "expected_git_head", "") or ""),
            )
    else:
        cases = resolve_case_source_paths(selected_cases)
    if is_v2:
        try:
            report_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise ReplayConfigError(
                f"v2 report directory already exists; refusing replacement: {report_dir}"
            ) from exc
    else:
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

    git_before = _git_status()
    dirty_repo_before = _dirty_repo_file_snapshot(git_before, report_dir)
    source_before = _source_snapshot(cases)
    cache_roots = _normal_cache_roots(cases)
    normal_cache_before = _normal_cache_snapshot(cases, cache_roots)

    with tempfile.TemporaryDirectory(
        prefix=APPROVED_TMP_PREFIX.removeprefix("/tmp/"), dir="/tmp"
    ) as tmp_dir:
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
        cache_ok, cache_root_text, cache_error, cache_verification_mode = (
            _check_cache_root(data_root)
        )
        input_manifest = {
            "manifest_path": str(manifest_path),
            "manifest_sha256": _sha256(manifest_path),
            "manifest_artifact_type": manifest.get("artifact_type"),
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
        if is_v2:
            input_manifest["source_contract"] = {
                "path": V2_CORPUS_REPO_PATH.as_posix(),
                "sha256": V2_CORPUS_SHA256,
            }
            if receipt is None:
                input_manifest["invocation_receipt"] = {
                    "created": False,
                    "preflight_only": True,
                }
            else:
                receipt_path = Path(str(args.invocation_receipt))
                input_manifest["invocation_receipt"] = {
                    "path": str(receipt_path),
                    "sha256": _sha256(receipt_path),
                    "invocation_id": receipt.get("invocation_id"),
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
                execution_cases = (
                    _materialize_v2_execution_sources(
                        cases, data_root / "v2_bound_sources"
                    )
                    if is_v2
                    else cases
                )
                results, llm_info = _run_cases(
                    execution_cases,
                    llm_url,
                    log_path,
                    case_timeout_seconds=int(args.case_timeout_seconds),
                    include_benchmark_internal_metrics=is_v2,
                    expected_code_identity=(
                        receipt.get("code_identity")
                        if is_v2 and receipt is not None
                        else None
                    ),
                )
            except CodeIdentityConflict as exc:
                code_identity_conflict = str(exc)
                results, llm_info = _runner_exception_payload(exc)
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"code_identity_conflict {exc}\n")
            except Exception as exc:
                results, llm_info = _runner_exception_payload(exc)
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(
                        f"runner_exception status={llm_info.get('status')} "
                        f"classification={llm_info.get('classification')} "
                        f"{type(exc).__name__}: {exc}\n"
                    )

        isolated_cache_files = _list_files(Path(cache_root_text))
        isolated_runtime_files = _list_files(data_root)

        if is_v2 and receipt is not None and not args.preflight_only:
            try:
                require_v2_code_identity(receipt.get("code_identity"))
            except CodeIdentityConflict as exc:
                code_identity_conflict = str(exc)
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"code_identity_conflict_before_publication {exc}\n")

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
        code_identity_conflict=code_identity_conflict,
    )
    extraction_exceptions = [
        row for row in results if (row.get("result") or {}).get("status") == "exception"
    ]
    infrastructure_failures = [
        row
        for row in results
        if _is_infrastructure_failure(row, include_raw_transport=is_v2)
    ]
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
        "artifact_type": (
            "extraction_no_write_replay_results_v2"
            if is_v2
            else "extraction_no_write_replay_results_v1"
        ),
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
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        help="Certified case id/ticker/document id, or all.",
    )
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--llm-base-url", default="")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=DEFAULT_SHARED_DATA_ROOT,
        help=(
            "Root used only to resolve v2 repo-relative declared source paths. "
            "No fallback candidates are searched."
        ),
    )
    parser.add_argument(
        "--source-contract",
        type=Path,
        default=None,
        help=(
            "Physical path to the exact hash-bound v2 corpus. The manifest's "
            "declared logical source_contract path remains fixed."
        ),
    )
    parser.add_argument(
        "--invocation-receipt",
        default="",
        help="Existing exclusive v2 receipt required for a non-preflight v2 launch.",
    )
    parser.add_argument(
        "--expected-git-head",
        default="",
        help="Exact clean Git HEAD bound by the outer v2 one-shot runner.",
    )
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
    parser.add_argument(
        "--_profile-reexeced",
        action="store_true",
        dest="_profile_reexeced",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate manifest, sources, env, isolated cache, and side-effect audit without calling extraction.",
    )
    parser.add_argument(
        "--case-timeout-seconds",
        type=int,
        default=DEFAULT_CASE_TIMEOUT_SECONDS,
        help=(
            "Maximum seconds for each extraction case before recording an infrastructure "
            "DATA_MISSING timeout. Use 0 to disable."
        ),
    )
    return parser.parse_args()


def main() -> int:
    try:
        return run_replay(parse_args())
    except CodeIdentityConflict as exc:
        print(
            json.dumps(
                {"status": "EVIDENCE_CONFLICT", "error": str(exc)},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return CODE_IDENTITY_CONFLICT_EXIT_CODE
    except ReplayConfigError as exc:
        print(
            json.dumps({"status": "FAIL", "error": str(exc)}, indent=2, sort_keys=True),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
