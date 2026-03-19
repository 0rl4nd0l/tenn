"""Configuration loading for autodev runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AutoDevConfig:
    repo_path: Path
    default_branch: str
    max_retries: int
    allow_network: bool
    pr_mode: str
    notification_mode: str
    notification_webhook_file: Path | None
    daemon_interval_seconds: int
    gate_timeout_seconds: int
    use_docker_if_available: bool
    docker_image: str
    dockerfile_path: str
    docker_auto_build: bool
    max_changed_lines_per_attempt: int
    max_changed_files_per_attempt: int
    worker_name: str
    llm_routing_mode: str
    llm_provider_balanced: str
    llm_provider_heavy: str
    llama_cpp_base_url: str
    llama_cpp_api_key: str
    llama_cpp_model_balanced: str
    llama_cpp_model_heavy: str
    ollama_host: str
    ollama_model_balanced: str
    ollama_model_heavy: str
    ollama_timeout_seconds: int
    openai_model: str
    llm_max_generation_attempts: int
    allowed_paths: tuple[str, ...]
    protected_paths: tuple[str, ...]
    baseline_path: Path
    allow_baseline_init: bool
    allow_baseline_update: bool
    protected_metrics: tuple[str, ...]
    regression_tolerances: dict[str, float]
    enable_debate: bool
    debate_strictness: str
    debate_require_3_failure_modes: bool
    python_bin: str
    enable_task_discovery: bool = False
    discovery_interval_seconds: int = 900


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _read_yaml_config(yaml_path: Path) -> dict[str, Any]:
    if not yaml_path.exists():
        return {}
    try:
        import yaml  # type: ignore
    except Exception:
        # Lightweight fallback parser for simple `key: value` config files.
        # This keeps autodev usable even when PyYAML is not installed.
        parsed: dict[str, Any] = {}
        for raw_line in yaml_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            lowered = value.lower()
            if lowered in {"true", "false"}:
                parsed[key] = lowered == "true"
            else:
                parsed[key] = value
        return parsed
    with yaml_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}


def _parse_json_float_dict(value: str, default: dict[str, float] | None = None) -> dict[str, float]:
    base = default or {}
    try:
        raw = json.loads(value)
    except Exception:
        return dict(base)
    if not isinstance(raw, dict):
        return dict(base)
    out: dict[str, float] = {}
    for key, item in raw.items():
        try:
            out[str(key)] = float(item)
        except (TypeError, ValueError):
            continue
    return out


def _env_or_yaml(
    env_name: str,
    yaml_data: dict[str, Any],
    yaml_key: str,
    default: Any,
) -> Any:
    env_value = os.environ.get(env_name)
    if env_value is not None:
        return env_value
    return yaml_data.get(yaml_key, default)


def load_config() -> AutoDevConfig:
    repo_path = Path(__file__).resolve().parents[2]
    yaml_path = repo_path / "autodev" / "autodev.yaml"
    yaml_data = _read_yaml_config(yaml_path)

    repo_path_value = _env_or_yaml("AUTODEV_REPO_PATH", yaml_data, "repo_path", str(repo_path))
    default_branch = str(_env_or_yaml("AUTODEV_DEFAULT_BRANCH", yaml_data, "default_branch", "main"))
    max_retries = _parse_int(
        str(_env_or_yaml("AUTODEV_MAX_RETRIES", yaml_data, "max_retries", 10)),
        10,
    )
    allow_network = _parse_bool(
        str(_env_or_yaml("AUTODEV_ALLOW_NETWORK", yaml_data, "allow_network", False)),
        False,
    )
    pr_mode = str(_env_or_yaml("AUTODEV_PR_MODE", yaml_data, "pr_mode", "local_patch"))
    notification_mode = str(
        _env_or_yaml("AUTODEV_NOTIFICATION_MODE", yaml_data, "notification_mode", "stdout")
    )
    webhook_raw = _env_or_yaml(
        "AUTODEV_NOTIFICATION_WEBHOOK_FILE",
        yaml_data,
        "notification_webhook_file",
        "",
    )
    daemon_interval_seconds = _parse_int(
        str(_env_or_yaml("AUTODEV_DAEMON_INTERVAL_SECONDS", yaml_data, "daemon_interval_seconds", 300)),
        300,
    )
    gate_timeout_seconds = _parse_int(
        str(_env_or_yaml("AUTODEV_GATE_TIMEOUT_SECONDS", yaml_data, "gate_timeout_seconds", 600)),
        600,
    )
    use_docker_if_available = _parse_bool(
        str(_env_or_yaml("AUTODEV_USE_DOCKER", yaml_data, "use_docker_if_available", True)),
        True,
    )
    docker_image = str(_env_or_yaml("AUTODEV_DOCKER_IMAGE", yaml_data, "docker_image", "autodev-gates:latest"))
    dockerfile_path = str(
        _env_or_yaml("AUTODEV_DOCKERFILE_PATH", yaml_data, "dockerfile_path", "autodev/docker/Dockerfile")
    )
    docker_auto_build = _parse_bool(
        str(_env_or_yaml("AUTODEV_DOCKER_AUTO_BUILD", yaml_data, "docker_auto_build", True)),
        True,
    )
    max_changed_lines_per_attempt = _parse_int(
        str(
            _env_or_yaml(
                "AUTODEV_MAX_CHANGED_LINES_PER_ATTEMPT",
                yaml_data,
                "max_changed_lines_per_attempt",
                300,
            )
        ),
        300,
    )
    max_changed_files_per_attempt = _parse_int(
        str(
            _env_or_yaml(
                "AUTODEV_MAX_CHANGED_FILES",
                yaml_data,
                "max_changed_files_per_attempt",
                20,
            )
        ),
        20,
    )
    worker_name = str(_env_or_yaml("AUTODEV_WORKER", yaml_data, "worker", "local_patch"))
    llm_routing_mode = str(
        _env_or_yaml("AUTODEV_LLM_ROUTING_MODE", yaml_data, "llm_routing_mode", "simple")
    )
    llm_provider_balanced = str(
        _env_or_yaml(
            "AUTODEV_LLM_PROVIDER_BALANCED",
            yaml_data,
            "llm_provider_balanced",
            "llamacpp",
        )
    )
    llm_provider_heavy = str(
        _env_or_yaml(
            "AUTODEV_LLM_PROVIDER_HEAVY",
            yaml_data,
            "llm_provider_heavy",
            "llamacpp",
        )
    )
    llama_cpp_base_url = str(
        _env_or_yaml(
            "AUTODEV_LLAMA_CPP_BASE_URL",
            yaml_data,
            "llama_cpp_base_url",
            "http://127.0.0.1:8000/v1",
        )
    )
    llama_cpp_api_key = str(
        _env_or_yaml(
            "AUTODEV_LLAMA_CPP_API_KEY",
            yaml_data,
            "llama_cpp_api_key",
            "local-openai-key",
        )
    )
    llama_cpp_model_balanced = str(
        _env_or_yaml(
            "AUTODEV_LLAMA_CPP_MODEL_BALANCED",
            yaml_data,
            "llama_cpp_model_balanced",
            "qwen2.5-coder-14b",
        )
    )
    llama_cpp_model_heavy = str(
        _env_or_yaml(
            "AUTODEV_LLAMA_CPP_MODEL_HEAVY",
            yaml_data,
            "llama_cpp_model_heavy",
            "qwen2.5-coder-14b",
        )
    )
    ollama_host = str(
        _env_or_yaml("AUTODEV_OLLAMA_HOST", yaml_data, "ollama_host", "http://127.0.0.1:11434")
    )
    ollama_model_balanced = str(
        _env_or_yaml(
            "AUTODEV_OLLAMA_MODEL_BALANCED",
            yaml_data,
            "ollama_model_balanced",
            "qwen2.5-coder:7b",
        )
    )
    ollama_model_heavy = str(
        _env_or_yaml(
            "AUTODEV_OLLAMA_MODEL_HEAVY",
            yaml_data,
            "ollama_model_heavy",
            "qwen2.5:32b",
        )
    )
    ollama_timeout_seconds = _parse_int(
        str(
            _env_or_yaml(
                "AUTODEV_OLLAMA_TIMEOUT_SECONDS",
                yaml_data,
                "ollama_timeout_seconds",
                120,
            )
        ),
        120,
    )
    openai_model = str(
        _env_or_yaml("AUTODEV_OPENAI_MODEL", yaml_data, "openai_model", "gpt-4.1-mini")
    )
    llm_max_generation_attempts = _parse_int(
        str(
            _env_or_yaml(
                "AUTODEV_LLM_MAX_ATTEMPTS",
                yaml_data,
                "llm_max_generation_attempts",
                3,
            )
        ),
        3,
    )
    allowed_paths_raw = str(
        _env_or_yaml(
            "AUTODEV_ALLOWED_PATHS",
            yaml_data,
            "allowed_paths",
            "autodev/",
        )
    )
    allowed_paths = tuple(
        item.strip() for item in allowed_paths_raw.split(",") if item.strip()
    )
    if not allowed_paths:
        allowed_paths = ("autodev/",)
    protected_paths_raw = str(
        _env_or_yaml(
            "AUTODEV_PROTECTED_PATHS",
            yaml_data,
            "protected_paths",
            ".github/,financial-engine_v2/,scripts/,docs/",
        )
    )
    protected_paths = tuple(
        item.strip() for item in protected_paths_raw.split(",") if item.strip()
    )
    baseline_path_raw = str(
        _env_or_yaml(
            "AUTODEV_BASELINE_PATH",
            yaml_data,
            "baseline_path",
            "autodev/baselines/baseline_metrics.json",
        )
    )
    allow_baseline_init = _parse_bool(
        str(_env_or_yaml("AUTODEV_ALLOW_BASELINE_INIT", yaml_data, "allow_baseline_init", 0)),
        False,
    )
    allow_baseline_update = _parse_bool(
        str(_env_or_yaml("AUTODEV_ALLOW_BASELINE_UPDATE", yaml_data, "allow_baseline_update", 0)),
        False,
    )
    protected_metrics_raw = str(
        _env_or_yaml("AUTODEV_PROTECTED_METRICS", yaml_data, "protected_metrics", "")
    )
    protected_metrics = tuple(
        item.strip() for item in protected_metrics_raw.split(",") if item.strip()
    )
    tolerance_raw = str(
        _env_or_yaml(
            "AUTODEV_REGRESSION_TOLERANCE_JSON",
            yaml_data,
            "regression_tolerance_json",
            "{}",
        )
    )
    regression_tolerances = _parse_json_float_dict(tolerance_raw, default={})
    enable_debate = _parse_bool(
        str(_env_or_yaml("AUTODEV_ENABLE_DEBATE", yaml_data, "enable_debate", 1)),
        True,
    )
    debate_strictness = str(_env_or_yaml("AUTODEV_DEBATE_STRICTNESS", yaml_data, "debate_strictness", "strict"))
    debate_require_3_failure_modes = _parse_bool(
        str(
            _env_or_yaml(
                "AUTODEV_DEBATE_REQUIRE_3_FAILURE_MODES",
                yaml_data,
                "debate_require_3_failure_modes",
                1,
            )
        ),
        True,
    )
    python_bin = str(_env_or_yaml("AUTODEV_PYTHON_BIN", yaml_data, "python_bin", "python3"))
    enable_task_discovery = _parse_bool(
        str(_env_or_yaml("AUTODEV_ENABLE_TASK_DISCOVERY", yaml_data, "enable_task_discovery", 0)),
        False,
    )
    discovery_interval_seconds = _parse_int(
        str(
            _env_or_yaml(
                "AUTODEV_DISCOVERY_INTERVAL_SECONDS",
                yaml_data,
                "discovery_interval_seconds",
                900,
            )
        ),
        900,
    )

    webhook_file = Path(str(webhook_raw)) if str(webhook_raw).strip() else None
    baseline_path_obj = Path(baseline_path_raw)
    if not baseline_path_obj.is_absolute():
        baseline_path_obj = (Path(str(repo_path_value)).resolve() / baseline_path_obj).resolve()

    return AutoDevConfig(
        repo_path=Path(str(repo_path_value)).resolve(),
        default_branch=default_branch,
        max_retries=max_retries,
        allow_network=allow_network,
        pr_mode=pr_mode,
        notification_mode=notification_mode,
        notification_webhook_file=webhook_file,
        daemon_interval_seconds=daemon_interval_seconds,
        gate_timeout_seconds=gate_timeout_seconds,
        use_docker_if_available=use_docker_if_available,
        docker_image=docker_image,
        dockerfile_path=dockerfile_path,
        docker_auto_build=docker_auto_build,
        max_changed_lines_per_attempt=max_changed_lines_per_attempt,
        max_changed_files_per_attempt=max_changed_files_per_attempt,
        worker_name=worker_name,
        llm_routing_mode=llm_routing_mode,
        llm_provider_balanced=llm_provider_balanced,
        llm_provider_heavy=llm_provider_heavy,
        llama_cpp_base_url=llama_cpp_base_url,
        llama_cpp_api_key=llama_cpp_api_key,
        llama_cpp_model_balanced=llama_cpp_model_balanced,
        llama_cpp_model_heavy=llama_cpp_model_heavy,
        ollama_host=ollama_host,
        ollama_model_balanced=ollama_model_balanced,
        ollama_model_heavy=ollama_model_heavy,
        ollama_timeout_seconds=ollama_timeout_seconds,
        openai_model=openai_model,
        llm_max_generation_attempts=llm_max_generation_attempts,
        allowed_paths=allowed_paths,
        protected_paths=protected_paths,
        baseline_path=baseline_path_obj,
        allow_baseline_init=allow_baseline_init,
        allow_baseline_update=allow_baseline_update,
        protected_metrics=protected_metrics,
        regression_tolerances=regression_tolerances,
        enable_debate=enable_debate,
        debate_strictness=debate_strictness,
        debate_require_3_failure_modes=debate_require_3_failure_modes,
        python_bin=python_bin,
        enable_task_discovery=enable_task_discovery,
        discovery_interval_seconds=discovery_interval_seconds,
    )
