#!/usr/bin/env python3
"""Runtime entrypoint contract for Tenn docs and agent metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_CONTRACT_PATH = REPO_ROOT / "agent_contract.json"
ENTRYPOINTS_DOC = REPO_ROOT / "docs" / "entrypoints.md"
STARTUP_DOC = REPO_ROOT / "docs" / "startup.md"


@dataclass(frozen=True)
class RuntimeMode:
    mode: str
    audience: str
    status: str
    entrypoint: str
    command: str
    healthcheck_url: str | None = None
    ui_url: str | None = None
    validation: str | None = None
    notes: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        payload = asdict(self)
        payload["notes"] = list(self.notes)
        return {key: value for key, value in payload.items() if value is not None}


def runtime_modes() -> dict[str, RuntimeMode]:
    """Return the supported runtime modes and their stable entrypoints."""
    return {
        "agent_local_backend": RuntimeMode(
            mode="agent_local_backend",
            audience="agents and focused backend validation",
            status="canonical_for_agent_runtime_tasks",
            entrypoint="financial-engine_v2/scripts/run_local_backend.sh",
            command="LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh",
            healthcheck_url="http://127.0.0.1:8000/api/health",
            validation="scripts/validate_system.sh",
            notes=(
                "Uses the local backend script through scripts/start_system.sh for deterministic agent checks.",
                "Does not start the full Docker Compose stack unless the task explicitly requires it.",
            ),
        ),
        "full_stack_cockpit": RuntimeMode(
            mode="full_stack_cockpit",
            audience="operator UI and full infrastructure startup",
            status="canonical_for_operator_full_stack",
            entrypoint="scripts/cockpit",
            command="cockpit start new",
            healthcheck_url="http://127.0.0.1:8000/api/health",
            ui_url="http://127.0.0.1:8081",
            validation="cockpit doctor",
            notes=(
                "Uses Docker Compose for backend, worker, Redis, Postgres, and Qdrant.",
                "Launches the Next.js Cockpit UI after the full stack is started.",
            ),
        ),
        "batch_orchestrator": RuntimeMode(
            mode="batch_orchestrator",
            audience="batch workflow execution",
            status="supported_not_system_bootstrap",
            entrypoint="run.py",
            command="python run.py",
            notes=(
                "Runs batch workflows and may require external providers or network.",
                "Does not define the running system health contract.",
            ),
        ),
    }


def runtime_modes_json() -> dict[str, dict[str, object]]:
    return {name: mode.to_json() for name, mode in runtime_modes().items()}


def expected_agent_contract() -> dict[str, object]:
    """Return the expected machine-readable agent runtime contract."""
    return {
        "canonical_entrypoint": "financial-engine_v2/scripts/run_local_backend.sh",
        "recommended_wrapper": "scripts/start_system.sh",
        "venv_path": "financial-engine_v2/.venv",
        "default_profile": "isolated",
        "base_url": "http://127.0.0.1:8000",
        "healthcheck": "/api/health",
        "healthcheck_url": "http://127.0.0.1:8000/api/health",
        "validation": "scripts/validate_system.sh",
        "runtime_modes": runtime_modes_json(),
    }


def load_json(path: str | Path) -> dict[str, object]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _compare_dict(
    *,
    prefix: str,
    expected: Mapping[str, object],
    actual: Mapping[str, object],
) -> list[str]:
    issues: list[str] = []
    for key, expected_value in expected.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in actual:
            issues.append(f"missing {path}")
            continue
        actual_value = actual[key]
        if isinstance(expected_value, Mapping):
            if not isinstance(actual_value, Mapping):
                issues.append(f"{path} must be an object")
                continue
            issues.extend(_compare_dict(prefix=path, expected=expected_value, actual=actual_value))
        elif actual_value != expected_value:
            issues.append(f"{path} expected {expected_value!r} got {actual_value!r}")
    return issues


def check_agent_contract(path: str | Path = AGENT_CONTRACT_PATH) -> dict[str, object]:
    expected = expected_agent_contract()
    actual = load_json(path)
    issues = _compare_dict(prefix="", expected=expected, actual=actual)
    return {"ok": not issues, "issues": issues, "expected": expected, "actual": actual}


def _read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def check_docs(
    *,
    entrypoints_doc: str | Path = ENTRYPOINTS_DOC,
    startup_doc: str | Path = STARTUP_DOC,
) -> dict[str, object]:
    entrypoints_text = _read_text(entrypoints_doc)
    startup_text = _read_text(startup_doc)
    checks = {
        "entrypoints_agent_local_heading": "Agent-Local Backend Mode" in entrypoints_text,
        "entrypoints_full_stack_reference": "Full-Stack Cockpit Mode" in entrypoints_text,
        "entrypoints_batch_mode": "Batch Mode" in entrypoints_text,
        "startup_full_stack_heading": "Full-Stack Cockpit Mode" in startup_text,
        "startup_agent_local_reference": "Agent-Local Backend Mode" in startup_text,
        "startup_docker_scope": "only in Docker for this mode" in startup_text,
    }
    issues = [name for name, ok in checks.items() if not ok]
    return {"ok": not issues, "issues": issues, "checks": checks}


def validate_contract(
    *,
    agent_contract_path: str | Path = AGENT_CONTRACT_PATH,
    entrypoints_doc: str | Path = ENTRYPOINTS_DOC,
    startup_doc: str | Path = STARTUP_DOC,
) -> dict[str, object]:
    agent = check_agent_contract(agent_contract_path)
    docs = check_docs(entrypoints_doc=entrypoints_doc, startup_doc=startup_doc)
    issues = [*agent["issues"], *docs["issues"]]
    return {"ok": not issues, "issues": issues, "agent_contract": agent, "docs": docs}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the expected runtime mode contract as JSON.")
    parser.add_argument("--check", action="store_true", help="Validate agent_contract.json and runtime docs.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.json:
        print(json.dumps(expected_agent_contract(), indent=2, sort_keys=True))
        return 0
    result = validate_contract()
    print(json.dumps({"ok": result["ok"], "issues": result["issues"]}, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
