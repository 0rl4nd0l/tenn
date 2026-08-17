#!/usr/bin/env python3
"""Run the exact Issue #554 v2 corpus once, with fail-closed publication."""

from __future__ import annotations

import argparse
from collections import Counter
import ctypes
from dataclasses import asdict, fields, is_dataclass
from decimal import Decimal, InvalidOperation
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import time
import types
from typing import Any
from urllib.parse import urlparse
import uuid


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "financial-engine_v2" / "backend"
ActualCell: Any = None
BenchmarkContractError: type[Exception] = ValueError
CorpusDocument: Any = None
ExpectedCell: Any = None
METRICS: tuple[str, ...] = ()


DEFAULT_BUNDLE_ROOT = (
    REPO_ROOT / "financial-engine_v2/data/broad_extraction_benchmark/v2"
)
DEFAULT_CORPUS = DEFAULT_BUNDLE_ROOT / "corpus.json"
DEFAULT_EXPECTATIONS = DEFAULT_BUNDLE_ROOT / "expectations.json"
DEFAULT_SOURCE_MANIFEST = DEFAULT_BUNDLE_ROOT / "source_manifest.json"
DEFAULT_CASE_MANIFEST = (
    REPO_ROOT
    / "financial-engine_v2/data/extraction_no_write_cases/issue554_broad_corpus_v2.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / "reports/agent_jobs/issue554_broad_corpus_baseline_v2_20260816/baseline"
)
DEFAULT_SHARED_DATA_ROOT = Path("/mnt/tenn-nvme2/tenn/financial-engine_v2/data")
RECEIPT_NAME = "INVOCATION_RECEIPT.json"
EXPECTED_CASE_COUNT = 20
CODE_IDENTITY_CONFLICT_EXIT_CODE = 3
EXPECTED_INPUT_SHA256 = {
    "corpus": "815649beffc63946eeeb77771deb961e1f36f06ee5ec49c9cd6ac068a49323dd",
    "expectations": "5e8536d976255c33495a9945c7ecae448fd2f3e5ba5c4b35849457bb6425d2d9",
    "source_manifest": "b3f319756541aa9da2ea3878922e81205d0207655ce5303b93c27c7466e252cf",
    "case_manifest": "fa1880e039ab86ae2f2d7d7ebd9444ead8fed4c362925f2105c668819898f741",
}
EXPECTED_SEMANTIC_DIGESTS = {
    "corpus": "1cd7ee56739aba1f782ec2e39b1bdda964aba9df6d508c25d0f565cb8c2da9c8",
    "contract": "521682ec9e214b551511e7a00669d93bd71ee8d5beef5ab651a531c8c2cfe54c",
}
METRIC_MAP = {
    "revenue": "revenue",
    "npat_attributable": "np_attributable",
    "operating_cash_flow": "operating_cf",
    "capital_expenditure": "capex",
    "cash_and_equivalents": "cash_end",
    "total_debt": "total_debt",
    "shares_outstanding": "shares_outstanding",
}
SCALE_MULTIPLIERS = {
    "units": Decimal(1),
    "thousands": Decimal(1_000),
    "millions": Decimal(1_000_000),
    "billions": Decimal(1_000_000_000),
    "trillions": Decimal(1_000_000_000_000),
}
RAW_UNIT_BY_SUFFIX = {
    "k": "thousands",
    "thousand": "thousands",
    "thousands": "thousands",
    "m": "millions",
    "mn": "millions",
    "million": "millions",
    "millions": "millions",
    "b": "billions",
    "bn": "billions",
    "billion": "billions",
    "billions": "billions",
    "t": "trillions",
    "tn": "trillions",
    "trillion": "trillions",
    "trillions": "trillions",
}
RAW_SOURCE_VALUE_RE = re.compile(
    r"^(?P<currency>(?:[A-Z]{1,3}\$|[A-Z]{3}|\$)\s*)?"
    r"(?P<num>[+-]?(?:\d+(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"\s*(?P<suffix>k|thousands?|mn|m|millions?|bn|b|billions?|tn|t|trillions?)?$",
    re.IGNORECASE,
)
IMPORT_PREFLIGHT_MODULES = (
    "httpx",
    "app.services.llm",
    "app.services.multipass_extraction",
)
EXPECTED_DEPENDENCY_VERSIONS = {
    "httpx": "0.27.2",
    "fastapi": "0.115.6",
    "pydantic": "2.9.2",
    "SQLAlchemy": "2.0.36",
    "celery": "5.4.0",
    "redis": "5.1.1",
    "PyMuPDF": "1.24.10",
}
EXPECTED_DEPENDENCY_IMPORTS = {
    "httpx": "httpx",
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "SQLAlchemy": "sqlalchemy",
    "celery": "celery",
    "redis": "redis",
    "PyMuPDF": "fitz",
}
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
LAUNCH_ENV_PASSTHROUGH = (
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
)
CODE_IDENTITY_PATHS = (
    "scripts/run_broad_extraction_benchmark_v2.py",
    "scripts/extraction_no_write_replay.py",
    "financial-engine_v2/backend/app/services/broad_extraction_benchmark.py",
    "financial-engine_v2/backend/app/services/multipass_extraction.py",
    "financial-engine_v2/backend/app/services/financial_metric_contract.py",
)
BENCHMARK_MODULE_PATH = (
    "financial-engine_v2/backend/app/services/broad_extraction_benchmark.py"
)


class RunnerError(RuntimeError):
    """Raised when v2 execution cannot proceed without weakening the contract."""


class CodeIdentityConflict(RunnerError):
    """Raised after receipt creation when execution code identity changes."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RunnerError(f"required input missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"unable to read valid JSON input: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RunnerError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise RunnerError(f"required input missing: {path}") from exc
    return digest.hexdigest()


def _require_regular_file(path: Path, label: str) -> None:
    if path.is_symlink() or not path.is_file():
        raise RunnerError(
            f"{label} must be an existing non-symlink regular file: {path}"
        )


def _normalize_report_path(path: Path, *, repo_root: Path = REPO_ROOT) -> Path:
    raw = Path(path)
    lexical = repo_root / raw if not raw.is_absolute() else raw
    if lexical.is_symlink():
        raise RunnerError(f"output root already exists; refusing symlink: {lexical}")
    resolved = lexical.resolve()
    allowed = (repo_root / "reports/agent_jobs").resolve()
    try:
        relative = resolved.relative_to(allowed)
    except ValueError as exc:
        raise RunnerError("output root must be under reports/agent_jobs") from exc
    if len(relative.parts) < 2:
        raise RunnerError("output root must name a job and an output directory")
    for parent in (repo_root / "reports", allowed, allowed / relative.parts[0]):
        if parent.exists() and parent.is_symlink():
            raise RunnerError(f"output path parent must not be a symlink: {parent}")
    return resolved


def _jsonable_score(score: Any) -> dict[str, Any]:
    def convert(value: Any) -> Any:
        if is_dataclass(value):
            return {
                field.name: convert(getattr(value, field.name))
                for field in fields(value)
            }
        if isinstance(value, dict) or hasattr(value, "items"):
            return {str(key): convert(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [convert(item) for item in value]
        return value

    payload = convert(score)
    if not isinstance(payload, dict):
        raise RunnerError("benchmark score did not serialize to an object")
    return payload


def _load_contract(
    corpus_payload: dict[str, Any], expectations_payload: dict[str, Any]
) -> tuple[tuple[CorpusDocument, ...], tuple[ExpectedCell, ...]]:
    if corpus_payload.get("artifact_type") != "broad_extraction_benchmark_corpus_v2":
        raise RunnerError("unsupported v2 corpus artifact_type")
    if (
        expectations_payload.get("artifact_type")
        != "broad_extraction_benchmark_expectations_v2"
    ):
        raise RunnerError("unsupported v2 expectations artifact_type")
    if tuple(expectations_payload.get("metrics") or ()) != METRICS:
        raise RunnerError(
            "v2 expectations metrics must equal the fixed ten-metric contract"
        )
    document_rows = corpus_payload.get("documents")
    expectation_rows = expectations_payload.get("documents")
    if not isinstance(document_rows, list) or not isinstance(expectation_rows, list):
        raise RunnerError("v2 corpus and expectations documents must be arrays")
    documents = tuple(
        CorpusDocument(
            document_id=str(row["document_id"]),
            issuer_id=str(row["issuer_id"]),
            document_class=str(row["document_class"]),
            period_type=str(row["period_type"]),
            period_end=str(row["period_end"]),
            admission_status=str(row["admission_status"]),
            source_path=row.get("source_path"),
            source_sha256=row.get("source_sha256"),
        )
        for row in document_rows
    )
    by_id = {
        row.get("document_id"): row for row in expectation_rows if isinstance(row, dict)
    }
    if len(by_id) != len(expectation_rows) or set(by_id) != {
        document.document_id for document in documents
    }:
        raise RunnerError(
            "v2 expectations must match every corpus document exactly once"
        )
    expectations: list[ExpectedCell] = []
    for document in documents:
        row = by_id[document.document_id]
        verified = row.get("verified")
        unresolved = row.get("unresolved_metrics")
        if not isinstance(verified, dict) or not isinstance(unresolved, list):
            raise RunnerError(f"{document.document_id}: invalid expectation block")
        verified_metrics = set(verified)
        unresolved_metrics = set(unresolved)
        if (
            verified_metrics & unresolved_metrics
            or verified_metrics | unresolved_metrics != set(METRICS)
            or len(unresolved_metrics) != len(unresolved)
        ):
            raise RunnerError(
                f"{document.document_id}: verified and unresolved cells must partition all ten metrics"
            )
        for metric in METRICS:
            if metric in verified:
                cell = verified[metric]
                expectations.append(
                    ExpectedCell(
                        document_id=document.document_id,
                        metric=metric,
                        applicability="applicable",
                        adjudication_status="verified",
                        raw_value=cell.get("raw_value"),
                        raw_unit=cell.get("raw_unit"),
                        currency=cell.get("currency"),
                        normalized_value=cell.get("normalized_value"),
                        evidence_location=cell.get("evidence_location"),
                    )
                )
            else:
                expectations.append(
                    ExpectedCell(
                        document_id=document.document_id,
                        metric=metric,
                        applicability="unresolved",
                        adjudication_status="unresolved",
                    )
                )
    return documents, tuple(expectations)


def _contract_digests(
    documents: tuple[CorpusDocument, ...], expectations: tuple[ExpectedCell, ...]
) -> dict[str, str]:
    document_rows = [
        asdict(item) for item in sorted(documents, key=lambda item: item.document_id)
    ]
    corpus_digest = hashlib.sha256(
        json.dumps(document_rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    contract_digest = hashlib.sha256(
        json.dumps(
            {
                "documents": document_rows,
                "expectations": [
                    asdict(item)
                    for item in sorted(
                        expectations,
                        key=lambda item: (item.document_id, item.metric),
                    )
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {"corpus": corpus_digest, "contract": contract_digest}


def _resolve_declared_source(path_text: str, source_root: Path) -> Path:
    declared = Path(path_text)
    if declared.is_absolute():
        return declared
    normalized = PurePosixPath(path_text.replace("\\", "/"))
    if any(part in {"", ".", ".."} for part in normalized.parts):
        raise RunnerError(f"invalid declared source path: {path_text}")
    return source_root.joinpath(*normalized.parts)


def validate_bundle(
    *,
    corpus_path: Path,
    expectations_path: Path,
    source_manifest_path: Path,
    case_manifest_path: Path,
    source_root: Path,
) -> dict[str, Any]:
    paths = {
        "corpus": corpus_path,
        "expectations": expectations_path,
        "source_manifest": source_manifest_path,
        "case_manifest": case_manifest_path,
    }
    observed_hashes: dict[str, str] = {}
    for label, path in paths.items():
        _require_regular_file(path, label)
        observed_hashes[label] = _sha256(path)
        if observed_hashes[label] != EXPECTED_INPUT_SHA256[label]:
            raise RunnerError(
                f"{label} SHA-256 mismatch: expected {EXPECTED_INPUT_SHA256[label]}, "
                f"observed {observed_hashes[label]}"
            )
    corpus_payload = _read_json(corpus_path)
    expectations_payload = _read_json(expectations_path)
    source_manifest = _read_json(source_manifest_path)
    case_manifest = _read_json(case_manifest_path)
    if (
        source_manifest.get("artifact_type")
        != "broad_extraction_benchmark_source_manifest_v2"
    ):
        raise RunnerError("unsupported v2 source manifest artifact_type")
    if case_manifest.get("artifact_type") != "extraction_no_write_case_manifest_v2":
        raise RunnerError("unsupported v2 case manifest artifact_type")
    certification = case_manifest.get("certification")
    if not isinstance(certification, dict):
        raise RunnerError("v2 case manifest certification must be an object")
    if certification.get("allow_production_writes") is not False:
        raise RunnerError("v2 case manifest must disallow production writes")
    if certification.get("loopback_llm_only") is not True:
        raise RunnerError("v2 case manifest must require loopback-only LLM access")
    if certification.get("source_contract") != (
        "financial-engine_v2/data/broad_extraction_benchmark/v2/corpus.json"
    ):
        raise RunnerError("v2 case manifest must declare the exact v2 corpus path")
    successor = source_manifest.get("successor")
    if not isinstance(successor, dict):
        raise RunnerError("v2 source manifest successor must be an object")
    source_manifest_hashes = {
        "corpus": successor.get("corpus_sha256"),
        "expectations": successor.get("expectations_sha256"),
        "case_manifest": successor.get("case_manifest_sha256"),
    }
    for label, declared_hash in source_manifest_hashes.items():
        if declared_hash != observed_hashes[label]:
            raise RunnerError(
                f"source manifest does not bind the exact {label} SHA-256"
            )
    documents, expectations = _load_contract(corpus_payload, expectations_payload)
    semantic_digests = _contract_digests(documents, expectations)
    if semantic_digests["corpus"] != EXPECTED_SEMANTIC_DIGESTS["corpus"]:
        raise RunnerError("v2 semantic corpus digest mismatch")
    if semantic_digests["contract"] != EXPECTED_SEMANTIC_DIGESTS["contract"]:
        raise RunnerError("v2 semantic contract digest mismatch")
    if successor.get("semantic_corpus_digest") != semantic_digests["corpus"]:
        raise RunnerError("source manifest semantic corpus digest mismatch")
    if successor.get("semantic_contract_digest") != semantic_digests["contract"]:
        raise RunnerError("source manifest semantic contract digest mismatch")
    if len(documents) != EXPECTED_CASE_COUNT or any(
        document.admission_status != "admitted" for document in documents
    ):
        raise RunnerError("v2 requires exactly 20 admitted corpus documents")
    cases = case_manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT:
        raise RunnerError("v2 case manifest must contain exactly 20 cases")
    document_by_id = {document.document_id: document for document in documents}
    seen_case_ids: set[str] = set()
    seen_document_ids: set[str] = set()
    resolved_cases: list[dict[str, Any]] = []
    for case in cases:
        if not isinstance(case, dict):
            raise RunnerError("v2 case rows must be objects")
        case_id = str(case.get("case_id") or "")
        document_id = str(case.get("document_id") or "")
        document = document_by_id.get(document_id)
        if (
            not case_id
            or case_id in seen_case_ids
            or document_id in seen_document_ids
            or document is None
        ):
            raise RunnerError("v2 cases must map one-to-one to corpus documents")
        if (
            case.get("ticker") != document.issuer_id
            or case.get("source_path") != document.source_path
        ):
            raise RunnerError(f"v2 case/corpus identity mismatch: {case_id}")
        source = _resolve_declared_source(str(case["source_path"]), source_root)
        _require_regular_file(source, f"source {case_id}")
        observed_source_hash = _sha256(source)
        if observed_source_hash != document.source_sha256:
            raise RunnerError(
                f"source SHA-256 mismatch for {case_id}: expected {document.source_sha256}, "
                f"observed {observed_source_hash}"
            )
        seen_case_ids.add(case_id)
        seen_document_ids.add(document_id)
        resolved = dict(case)
        resolved["resolved_source_path"] = str(source)
        resolved["source_sha256"] = observed_source_hash
        resolved_cases.append(resolved)
    if seen_document_ids != set(document_by_id):
        raise RunnerError("v2 case manifest omits corpus documents")
    return {
        "paths": {key: str(path) for key, path in paths.items()},
        "input_sha256": observed_hashes,
        "source_manifest": source_manifest,
        "documents": documents,
        "expectations": expectations,
        "cases": resolved_cases,
        "corpus_digest": semantic_digests["corpus"],
        "contract_digest": semantic_digests["contract"],
    }


def inspect_interpreter(python_bin: Path) -> dict[str, Any]:
    if not python_bin.is_absolute():
        raise RunnerError("python interpreter must be an explicit absolute path")
    if not python_bin.is_file() or not os.access(python_bin, os.X_OK):
        raise RunnerError(f"python interpreter is not executable: {python_bin}")
    command = [
        str(python_bin),
        "-c",
        (
            "import importlib, importlib.metadata, json, os, platform, site, sys; "
            f"mods={list(dict.fromkeys(IMPORT_PREFLIGHT_MODULES + tuple(EXPECTED_DEPENDENCY_IMPORTS.values())))!r}; "
            "[importlib.import_module(name) for name in mods]; "
            f"wanted={tuple(EXPECTED_DEPENDENCY_VERSIONS)!r}; "
            "versions={name: importlib.metadata.version(name) for name in wanted}; "
            "print(json.dumps({'executable':sys.executable,'python':platform.python_version(),"
            "'modules':mods,'versions':versions,'site_packages':[p for p in "
            "site.getsitepackages() if os.path.isdir(p) and not os.path.islink(p)]},"
            "sort_keys=True))"
        ),
    ]
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(BACKEND_ROOT),
    }
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RunnerError(f"interpreter import preflight failed: {detail}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RunnerError("interpreter import preflight returned invalid JSON") from exc
    versions = payload.get("versions")
    if versions != EXPECTED_DEPENDENCY_VERSIONS:
        raise RunnerError(
            "interpreter dependency versions mismatch: "
            f"expected {EXPECTED_DEPENDENCY_VERSIONS}, observed {versions}"
        )
    site_packages = payload.get("site_packages")
    if not isinstance(site_packages, list) or not site_packages:
        raise RunnerError("interpreter site-package binding is missing")
    for raw_path in site_packages:
        site_path = Path(str(raw_path))
        if (
            not site_path.is_absolute()
            or site_path.is_symlink()
            or not site_path.is_dir()
        ):
            raise RunnerError(
                f"interpreter site-package binding must be an absolute non-symlink directory: {site_path}"
            )
    payload["requested_path"] = str(python_bin)
    payload["binary_sha256"] = _sha256(python_bin.resolve())
    payload["dependency_snapshot_sha256"] = hashlib.sha256(
        json.dumps(payload["versions"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def replay_launch_environment() -> dict[str, str]:
    env = {
        key: value for key in LAUNCH_ENV_PASSTHROUGH if (value := os.environ.get(key))
    }
    env.update(
        {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        }
    )
    return env


def _git_output(*args: str) -> str:
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
        raise RunnerError(f"Git code-identity preflight failed: {detail}")
    return completed.stdout.strip()


def inspect_code_identity(expected_head: str) -> dict[str, Any]:
    expected = str(expected_head or "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", expected) is None:
        raise RunnerError(
            "expected Git HEAD must be an exact lowercase 40-character SHA"
        )
    observed = _git_output("rev-parse", "HEAD")
    if observed != expected:
        raise RunnerError(f"expected Git HEAD {expected}, observed {observed}")
    tracked_status = _git_output("status", "--porcelain=v1", "--untracked-files=no")
    if tracked_status:
        raise RunnerError(f"tracked worktree is not clean: {tracked_status}")
    code_status = _git_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        "scripts",
        "financial-engine_v2/backend",
    )
    if code_status:
        raise RunnerError(
            f"code paths contain untracked or modified files: {code_status}"
        )
    tree_sha = _git_output("show", "-s", "--format=%T", "HEAD")
    file_hashes: dict[str, str] = {}
    for relative in CODE_IDENTITY_PATHS:
        path = REPO_ROOT / relative
        _require_regular_file(path, f"code identity source {relative}")
        file_hashes[relative] = _sha256(path)
    return {
        "head_sha": observed,
        "tree_sha": tree_sha,
        "tracked_files_sha256": file_hashes,
    }


def require_unchanged_code_identity(binding: dict[str, Any]) -> None:
    expected_head = str(binding.get("head_sha") or "")
    try:
        observed = inspect_code_identity(expected_head)
    except (OSError, RunnerError) as exc:
        raise CodeIdentityConflict(
            f"execution code identity changed after receipt creation: {exc}"
        ) from exc
    if observed != binding:
        raise CodeIdentityConflict(
            "execution code identity changed after receipt creation"
        )


def load_bound_benchmark_module(binding: dict[str, Any]) -> types.ModuleType:
    require_unchanged_code_identity(binding)
    tracked_hashes = binding.get("tracked_files_sha256")
    if not isinstance(tracked_hashes, dict):
        raise CodeIdentityConflict("benchmark scorer code identity is invalid")
    expected_sha = str(tracked_hashes.get(BENCHMARK_MODULE_PATH) or "")
    source_path = REPO_ROOT / BENCHMARK_MODULE_PATH
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        source_fd = os.open(source_path, flags)
    except OSError as exc:
        raise CodeIdentityConflict("unable to open bound benchmark scorer") from exc
    try:
        if not stat.S_ISREG(os.fstat(source_fd).st_mode):
            raise CodeIdentityConflict("bound benchmark scorer is not a regular file")
        with os.fdopen(source_fd, "rb", closefd=False) as source_handle:
            source = source_handle.read()
    finally:
        os.close(source_fd)
    observed_sha = hashlib.sha256(source).hexdigest()
    if observed_sha != expected_sha:
        raise CodeIdentityConflict("bound benchmark scorer source SHA-256 mismatch")

    module_name = f"_tenn_bound_benchmark_{observed_sha}"
    module = types.ModuleType(module_name)
    module.__file__ = str(source_path)
    module.__package__ = "app.services"
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(source_path), "exec"), module.__dict__)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    require_unchanged_code_identity(binding)
    return module


def bind_benchmark_module(module: types.ModuleType) -> None:
    required = (
        "ActualCell",
        "BenchmarkContractError",
        "CorpusDocument",
        "ExpectedCell",
        "METRICS",
        "score_benchmark",
    )
    if any(not hasattr(module, name) for name in required):
        raise CodeIdentityConflict("bound benchmark scorer exports are incomplete")
    global ActualCell, BenchmarkContractError, CorpusDocument, ExpectedCell, METRICS
    ActualCell = module.ActualCell
    BenchmarkContractError = module.BenchmarkContractError
    CorpusDocument = module.CorpusDocument
    ExpectedCell = module.ExpectedCell
    METRICS = tuple(module.METRICS)


def score_with_bound_benchmark(
    module: types.ModuleType,
    documents: tuple[CorpusDocument, ...],
    expectations: tuple[ExpectedCell, ...],
    actuals: tuple[ActualCell, ...],
) -> Any:
    bound_documents = tuple(module.CorpusDocument(**asdict(row)) for row in documents)
    bound_expectations = tuple(
        module.ExpectedCell(**asdict(row)) for row in expectations
    )
    bound_actuals = tuple(module.ActualCell(**asdict(row)) for row in actuals)
    return module.score_benchmark(
        bound_documents,
        bound_expectations,
        bound_actuals,
    )


def require_fresh_authority(output_root: Path, receipt_path: Path) -> None:
    if output_root.exists() or output_root.is_symlink():
        raise RunnerError(
            f"output root already exists; refusing replacement: {output_root}"
        )
    if receipt_path.exists():
        raise RunnerError(
            f"invocation receipt already exists; authority is consumed: {receipt_path}"
        )
    if receipt_path.is_symlink():
        raise RunnerError(
            f"invocation receipt path must not be a symlink: {receipt_path}"
        )


def resolve_authority_paths(
    output_root_arg: Path, receipt_path_arg: Path
) -> tuple[Path, Path]:
    output_root = _normalize_report_path(output_root_arg)
    receipt_path = Path(receipt_path_arg).resolve()
    expected_receipt = output_root.parent / RECEIPT_NAME
    if receipt_path != expected_receipt:
        raise RunnerError(f"receipt path must be exactly {expected_receipt}")
    return output_root, receipt_path


def create_invocation_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise RunnerError(
            f"invocation receipt already exists; authority is consumed: {path}"
        ) from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # The exclusive file is intentionally retained: creation consumed authority.
        raise


def _renameat2_function() -> Any:
    try:
        libc = ctypes.CDLL(None, use_errno=True)
    except OSError as exc:
        raise RunnerError(
            "atomic no-replace directory publication is unavailable"
        ) from exc
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RunnerError("atomic no-replace directory publication is unavailable")
    return renameat2


def _rename_noreplace(renameat2: Any, source: Path, destination: Path) -> int | None:
    ctypes.set_errno(0)
    result = renameat2(
        -100,
        os.fsencode(source),
        -100,
        os.fsencode(destination),
        1,
    )
    return None if result == 0 else ctypes.get_errno()


def require_atomic_publish_capability(output_parent: Path) -> None:
    renameat2 = _renameat2_function()
    try:
        if output_parent.is_symlink():
            raise RunnerError(
                f"output path parent must not be a symlink: {output_parent}"
            )
        output_parent.mkdir(parents=True, exist_ok=True)
        if output_parent.is_symlink() or not output_parent.is_dir():
            raise RunnerError(
                f"output path parent must be a non-symlink directory: {output_parent}"
            )
        with tempfile.TemporaryDirectory(
            prefix=".atomic-publish-probe-", dir=output_parent
        ) as directory:
            probe_root = Path(directory)
            source = probe_root / "source"
            published = probe_root / "published"
            source.mkdir()
            error = _rename_noreplace(renameat2, source, published)
            if error is not None or source.exists() or not published.is_dir():
                detail = (
                    os.strerror(error) if error is not None else "verification failed"
                )
                raise RunnerError(
                    "atomic no-replace directory publication is unavailable on "
                    f"output filesystem {output_parent}: {detail}"
                )

            collision_source = probe_root / "collision-source"
            collision_destination = probe_root / "collision-destination"
            collision_source.mkdir()
            collision_destination.mkdir()
            error = _rename_noreplace(
                renameat2, collision_source, collision_destination
            )
            if error not in {errno.EEXIST, errno.ENOTEMPTY}:
                detail = (
                    "existing directory was replaced"
                    if error is None
                    else os.strerror(error)
                )
                raise RunnerError(
                    "atomic no-replace directory publication is unavailable on "
                    f"output filesystem {output_parent}: {detail}"
                )
            if not collision_source.is_dir() or not collision_destination.is_dir():
                raise RunnerError(
                    "atomic no-replace directory publication failed preservation "
                    f"verification on output filesystem {output_parent}"
                )
    except RunnerError:
        raise
    except OSError as exc:
        raise RunnerError(
            "atomic no-replace directory publication probe failed on output "
            f"filesystem {output_parent}: {exc}"
        ) from exc


def atomic_publish(stage_root: Path, output_root: Path) -> None:
    if not stage_root.is_dir():
        raise RunnerError(f"staging root missing: {stage_root}")
    renameat2 = _renameat2_function()
    error = _rename_noreplace(renameat2, stage_root, output_root)
    if error is not None:
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise RunnerError(f"output root appeared before publication: {output_root}")
        raise RunnerError(f"atomic publication failed: {os.strerror(error)}")


def require_complete_results(
    cases: list[dict[str, Any]], replay_payload: dict[str, Any]
) -> list[dict[str, Any]]:
    if replay_payload.get("artifact_type") != "extraction_no_write_replay_results_v2":
        raise RunnerError("scoring requires v2 replay results artifact_type")
    results = replay_payload.get("results")
    if not isinstance(results, list):
        raise RunnerError("replay results must be an array")
    if any(
        not isinstance(row, dict) or not isinstance(row.get("result"), dict)
        for row in results
    ):
        raise RunnerError("scoring requires a result object for every declared case")
    expected = {(str(case["case_id"]), str(case["document_id"])) for case in cases}
    observed = [
        (str(row.get("case_id") or ""), str(row.get("document_id") or ""))
        for row in results
        if isinstance(row, dict)
    ]
    if (
        len(results) != EXPECTED_CASE_COUNT
        or len(set(observed)) != len(observed)
        or set(observed) != expected
    ):
        raise RunnerError("scoring requires all 20 declared case results exactly once")
    return results


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _raw_source_identity(
    source_cell: dict[str, Any], fallback_unit: Any, normalized: Decimal
) -> tuple[str, str, str | None] | None:
    raw_text = " ".join(str(source_cell.get("raw_value") or "").split()).strip()
    negative_parentheses = raw_text.startswith("(") and raw_text.endswith(")")
    if negative_parentheses:
        raw_text = raw_text[1:-1].strip()
    match = RAW_SOURCE_VALUE_RE.fullmatch(raw_text)
    if match is None:
        return None
    try:
        raw_value = Decimal(match.group("num").replace(",", ""))
    except InvalidOperation:
        return None
    if negative_parentheses:
        raw_value = -abs(raw_value)
    suffix = str(match.group("suffix") or "").lower()
    raw_unit = RAW_UNIT_BY_SUFFIX.get(suffix) if suffix else str(fallback_unit or "")
    currency_text = str(match.group("currency") or "").upper().replace(" ", "")
    source_currency: str | None = None
    if currency_text and currency_text != "$":
        currency_letters = currency_text.removesuffix("$")
        source_currency = {
            "A": "AUD",
            "AU": "AUD",
            "C": "CAD",
            "CA": "CAD",
            "HK": "HKD",
            "NZ": "NZD",
            "S": "SGD",
            "SG": "SGD",
            "US": "USD",
        }.get(currency_letters)
        if source_currency is None and len(currency_letters) == 3:
            source_currency = currency_letters
        if source_currency is None:
            return None
    multiplier = SCALE_MULTIPLIERS.get(raw_unit)
    if multiplier is None or raw_value * multiplier != normalized:
        return None
    return _decimal_text(raw_value), raw_unit, source_currency


def _accepted_cell(
    document: CorpusDocument,
    metric: str,
    source_metric: str,
    payload: dict[str, Any],
) -> ActualCell | None:
    internal_metric = source_metric == "total_debt"
    values = (
        payload.get("benchmark_internal_metrics")
        if internal_metric
        else payload.get("non_null_metrics")
    ) or {}
    if source_metric not in values:
        return None
    scale_key = (
        "benchmark_internal_metric_source_scales"
        if internal_metric
        else "metric_source_scales"
    )
    provenance_key = (
        "benchmark_internal_provenance" if internal_metric else "provenance"
    )
    source_cells_key = (
        "benchmark_internal_source_cells"
        if internal_metric
        else "benchmark_metric_source_cells"
    )
    raw_unit = (payload.get(scale_key) or {}).get(source_metric) or payload.get("scale")
    try:
        normalized = Decimal(str(values[source_metric]))
    except (InvalidOperation, TypeError, ValueError):
        return None
    source_cell = (payload.get(source_cells_key) or {}).get(source_metric)
    if not isinstance(source_cell, dict) or source_cell.get(
        "requested_period_end"
    ) != payload.get("period_end"):
        return None
    raw_identity = _raw_source_identity(source_cell, raw_unit, normalized)
    if raw_identity is None:
        return None
    raw_value, raw_unit, source_currency = raw_identity
    provenance = (payload.get(provenance_key) or {}).get(source_metric)
    currency = (
        None
        if metric == "shares_outstanding"
        else source_currency or payload.get("currency")
    )
    if (
        not payload.get("period_type")
        or not payload.get("period_end")
        or not provenance
        or (metric != "shares_outstanding" and not currency)
    ):
        return None
    return ActualCell(
        document_id=document.document_id,
        metric=metric,
        status="accepted",
        raw_value=raw_value,
        raw_unit=str(raw_unit),
        normalized_value=_decimal_text(normalized),
        period_type=str(payload["period_type"]),
        period_end=str(payload["period_end"]),
        currency=str(currency) if currency is not None else None,
        source_sha256=document.source_sha256,
        evidence_location=str(provenance),
    )


def require_scoreable_replay(
    validation: dict[str, Any], replay: dict[str, Any], returncode: int
) -> None:
    validation_status = validation.get("status")
    replay_status = replay.get("status")
    if validation_status not in {"PASS", "FAIL", "DATA_MISSING"}:
        raise RunnerError("replay validation status is missing or invalid")
    if replay_status != validation_status:
        raise RunnerError("replay and validation status disagree")
    infrastructure_count = validation.get("infrastructure_failure_count")
    if (
        isinstance(infrastructure_count, bool)
        or not isinstance(infrastructure_count, int)
        or infrastructure_count < 0
    ):
        raise RunnerError("replay infrastructure_failure_count is missing or invalid")
    llm_info = validation.get("llm_info")
    if not isinstance(llm_info, dict):
        raise RunnerError("replay llm_info is missing or invalid")
    if (
        validation_status == "DATA_MISSING"
        or infrastructure_count
        or llm_info.get("status") == "DATA_MISSING"
    ):
        raise RunnerError("replay infrastructure evidence is incomplete")
    expected_returncode = 0 if validation_status == "PASS" else 2
    if returncode != expected_returncode:
        raise RunnerError("replay process status and return code disagree")


def actuals_from_replay(
    documents: tuple[CorpusDocument, ...], replay_payload: dict[str, Any]
) -> tuple[ActualCell, ...]:
    document_by_id = {document.document_id: document for document in documents}
    actuals: list[ActualCell] = []
    for row in replay_payload["results"]:
        document = document_by_id[str(row["document_id"])]
        payload = row.get("result") or {}
        for metric in METRICS:
            source_metric = METRIC_MAP.get(metric)
            if source_metric is None:
                actuals.append(
                    ActualCell(
                        document_id=document.document_id,
                        metric=metric,
                        status="unsupported",
                    )
                )
                continue
            accepted = None
            if payload.get("status") in {"ok", "ok_low_confidence"}:
                accepted = _accepted_cell(document, metric, source_metric, payload)
            actuals.append(
                accepted
                or ActualCell(
                    document_id=document.document_id, metric=metric, status="abstained"
                )
            )
    return tuple(actuals)


def _failure_attribution(score: dict[str, Any]) -> dict[str, Any]:
    by_metric: Counter[str] = Counter()
    by_issuer: Counter[str] = Counter()
    for row in score["rows"]:
        if row["outcome"] != "correct":
            by_metric[f"{row['metric']}:{row['outcome']}"] += 1
            by_issuer[f"{row['issuer_id']}:{row['outcome']}"] += 1
    return {
        "artifact_type": "broad_extraction_failure_attribution_v2",
        "outcome_counts": score["outcome_counts"],
        "identity_mismatch_counts": score["identity_mismatch_counts"],
        "by_metric_and_outcome": dict(sorted(by_metric.items())),
        "by_issuer_and_outcome": dict(sorted(by_issuer.items())),
        "gate_passed": score["gate_passed"],
    }


def _artifact_files(root: Path, *, exclude: set[str] | None = None) -> list[Path]:
    excluded = exclude or set()
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    ]


def seal_outputs(stage_root: Path) -> None:
    manifest_rows = [
        {
            "path": path.relative_to(stage_root).as_posix(),
            "sha256": _sha256(path),
            "size": path.stat().st_size,
        }
        for path in _artifact_files(
            stage_root, exclude={"OUTPUT_MANIFEST.json", "SHA256SUMS"}
        )
    ]
    _write_json(
        stage_root / "OUTPUT_MANIFEST.json",
        {
            "artifact_type": "broad_extraction_output_manifest_v2",
            "files": manifest_rows,
        },
    )
    lines = [
        f"{_sha256(path)}  {path.relative_to(stage_root).as_posix()}"
        for path in _artifact_files(stage_root, exclude={"SHA256SUMS"})
    ]
    (stage_root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _relative_report_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise RunnerError("replay staging path escaped repository") from exc


def _build_replay_command(args: argparse.Namespace, stage_root: Path) -> list[str]:
    return [
        str(args.python_bin),
        "-I",
        "-B",
        "-S",
        str(REPO_ROOT / "scripts/extraction_no_write_replay.py"),
        "--case-manifest",
        str(args.case_manifest),
        "--source-contract",
        str(args.corpus),
        "--case",
        "all",
        "--report-dir",
        _relative_report_path(stage_root / "replay"),
        "--profile",
        "baseline-no-write",
        "--llm-base-url",
        args.llm_base_url,
        "--case-timeout-seconds",
        str(args.case_timeout_seconds),
        "--source-root",
        str(args.source_root),
        "--invocation-receipt",
        str(args.receipt_path),
        "--expected-git-head",
        args.expected_git_head,
    ]


def validate_launch_settings(
    llm_base_url: str, case_timeout_seconds: int
) -> tuple[str, int]:
    url = str(llm_base_url or "").strip().rstrip("/")
    parsed = urlparse(url)
    try:
        parsed.port
    except ValueError as exc:
        raise RunnerError(f"LLM URL has an invalid port: {url}") from exc
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOOPBACK_HOSTS:
        raise RunnerError(f"LLM URL must be loopback http(s): {url}")
    try:
        timeout = int(case_timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise RunnerError("case timeout must be a positive integer") from exc
    if timeout <= 0:
        raise RunnerError("case timeout must be a positive integer")
    return url, timeout


def _run(args: argparse.Namespace) -> int:
    output_root, receipt_path = resolve_authority_paths(
        args.output_root, args.receipt_path
    )
    args.llm_base_url, args.case_timeout_seconds = validate_launch_settings(
        args.llm_base_url, args.case_timeout_seconds
    )
    require_fresh_authority(output_root, receipt_path)
    interpreter = inspect_interpreter(Path(args.python_bin))
    code_identity = inspect_code_identity(args.expected_git_head)
    bound_benchmark = load_bound_benchmark_module(code_identity)
    bind_benchmark_module(bound_benchmark)
    bundle = validate_bundle(
        corpus_path=Path(args.corpus).resolve(),
        expectations_path=Path(args.expectations).resolve(),
        source_manifest_path=Path(args.source_manifest).resolve(),
        case_manifest_path=Path(args.case_manifest).resolve(),
        source_root=Path(args.source_root).resolve(),
    )
    launch_environment = replay_launch_environment()
    require_fresh_authority(output_root, receipt_path)
    require_atomic_publish_capability(output_root.parent)
    invocation_id = uuid.uuid4().hex
    stage_root = output_root.parent / f".{output_root.name}.staging-{invocation_id}"
    if stage_root.exists() or stage_root.is_symlink():
        raise RunnerError(f"staging root already exists: {stage_root}")
    command = _build_replay_command(args, stage_root)
    receipt_payload = {
        "artifact_type": "broad_extraction_invocation_receipt_v2",
        "invocation_id": invocation_id,
        "created_unix_ns": time.time_ns(),
        "receipt_path": str(receipt_path),
        "final_output_root": str(output_root),
        "staging_root": str(stage_root),
        "replay_report_dir": str(stage_root / "replay"),
        "case_manifest_path": str(Path(args.case_manifest).resolve()),
        "case_manifest_sha256": bundle["input_sha256"]["case_manifest"],
        "corpus_path": str(Path(args.corpus).resolve()),
        "corpus_sha256": bundle["input_sha256"]["corpus"],
        "contract_digest": bundle["contract_digest"],
        "case_count": EXPECTED_CASE_COUNT,
        "interpreter": interpreter,
        "code_identity": code_identity,
        "launch_environment": launch_environment,
        "command": command,
    }
    # No fallible preflight belongs between this exclusive create and launch.
    create_invocation_receipt(receipt_path, receipt_payload)
    launch_error: str | None = None
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=launch_environment,
            check=False,
        )
    except OSError as exc:
        launch_error = f"replay launch failed: {exc}"
        completed = subprocess.CompletedProcess(command, 127)

    stage_root.mkdir(parents=True, exist_ok=True)
    _write_json(stage_root / RECEIPT_NAME, receipt_payload)
    _write_json(
        stage_root / "INPUT_BINDING.json",
        {
            "artifact_type": "broad_extraction_input_binding_v2",
            "input_sha256": bundle["input_sha256"],
            "corpus_digest": bundle["corpus_digest"],
            "contract_digest": bundle["contract_digest"],
            "source_count": len(bundle["cases"]),
            "interpreter": interpreter,
            "code_identity": code_identity,
            "launch_environment": launch_environment,
        },
    )
    _write_json(
        stage_root / "PREDECESSOR_EVIDENCE.json",
        {
            "artifact_type": "broad_extraction_predecessor_evidence_v2",
            "predecessor": bundle["source_manifest"].get("predecessor"),
            "successor": bundle["source_manifest"].get("successor"),
        },
    )
    terminal = "DATA_MISSING"
    score: dict[str, Any] | None = None
    error: str | None = launch_error
    try:
        if launch_error:
            raise RunnerError(launch_error)
        if completed.returncode == CODE_IDENTITY_CONFLICT_EXIT_CODE:
            raise CodeIdentityConflict(
                "child rejected execution code identity before report creation"
            )
        require_unchanged_code_identity(code_identity)
        validation = _read_json(stage_root / "replay/validation.json")
        side_effect_pass = validation.get("side_effect_pass")
        if side_effect_pass is False:
            terminal = "EVIDENCE_CONFLICT"
            error = "replay side-effect audit failed"
        elif side_effect_pass is not True:
            raise RunnerError(
                "replay validation side_effect_pass must be an explicit boolean"
            )
        else:
            replay = _read_json(stage_root / "replay/replay_results.json")
            require_complete_results(bundle["cases"], replay)
            require_scoreable_replay(validation, replay, completed.returncode)
            actuals = actuals_from_replay(bundle["documents"], replay)
            score = _jsonable_score(
                score_with_bound_benchmark(
                    bound_benchmark,
                    bundle["documents"],
                    bundle["expectations"],
                    actuals,
                )
            )
            terminal = "BASELINE_FROZEN_SCORED"
    except CodeIdentityConflict as exc:
        terminal = "EVIDENCE_CONFLICT"
        score = None
        error = str(exc)
    except (
        BenchmarkContractError,
        KeyError,
        OSError,
        RunnerError,
        TypeError,
        ValueError,
    ) as exc:
        error = str(exc)
    try:
        require_unchanged_code_identity(code_identity)
    except CodeIdentityConflict as exc:
        terminal = "EVIDENCE_CONFLICT"
        score = None
        error = str(exc)
    if terminal == "BASELINE_FROZEN_SCORED" and score is not None:
        _write_json(stage_root / "baseline_score.json", score)
        _write_json(
            stage_root / "failure_attribution.json",
            _failure_attribution(score),
        )
    _write_json(
        stage_root / "RUN_OUTCOME.json",
        {
            "artifact_type": "broad_extraction_run_outcome_v2",
            "terminal_state": terminal,
            "invocation_count": 1,
            "runner_returncode": completed.returncode,
            "case_count": EXPECTED_CASE_COUNT,
            "score_exists": score is not None,
            "error": error,
            "corpus_digest": bundle["corpus_digest"],
            "contract_digest": bundle["contract_digest"],
        },
    )
    seal_outputs(stage_root)
    atomic_publish(stage_root, output_root)
    print(
        json.dumps(
            {"terminal_state": terminal, "output_root": str(output_root)},
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if terminal == "BASELINE_FROZEN_SCORED" else 2


def _validate_only(args: argparse.Namespace) -> int:
    args.llm_base_url, args.case_timeout_seconds = validate_launch_settings(
        args.llm_base_url, args.case_timeout_seconds
    )
    output_root, receipt_path = resolve_authority_paths(
        args.output_root, args.receipt_path
    )
    require_fresh_authority(output_root, receipt_path)
    interpreter = inspect_interpreter(Path(args.python_bin))
    code_identity = inspect_code_identity(args.expected_git_head)
    bound_benchmark = load_bound_benchmark_module(code_identity)
    bind_benchmark_module(bound_benchmark)
    bundle = validate_bundle(
        corpus_path=Path(args.corpus).resolve(),
        expectations_path=Path(args.expectations).resolve(),
        source_manifest_path=Path(args.source_manifest).resolve(),
        case_manifest_path=Path(args.case_manifest).resolve(),
        source_root=Path(args.source_root).resolve(),
    )
    launch_environment = replay_launch_environment()
    require_atomic_publish_capability(output_root.parent)
    print(
        json.dumps(
            {
                "status": "PASS",
                "preflight_only": True,
                "receipt_created": False,
                "case_count": len(bundle["cases"]),
                "input_sha256": bundle["input_sha256"],
                "corpus_digest": bundle["corpus_digest"],
                "contract_digest": bundle["contract_digest"],
                "interpreter": interpreter,
                "code_identity": code_identity,
                "launch_environment": launch_environment,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--expectations", type=Path, default=DEFAULT_EXPECTATIONS)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--case-manifest", type=Path, default=DEFAULT_CASE_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SHARED_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--receipt-path",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT.parent / RECEIPT_NAME,
    )
    parser.add_argument("--python-bin", type=Path, required=True)
    parser.add_argument("--expected-git-head", required=True)
    parser.add_argument("--llm-base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--case-timeout-seconds", type=int, default=900)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        return _validate_only(args) if args.validate_only else _run(args)
    except (OSError, RunnerError, ValueError) as exc:
        print(
            json.dumps({"status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
