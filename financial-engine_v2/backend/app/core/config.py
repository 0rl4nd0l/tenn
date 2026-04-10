import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_ENV_FILE_NAMES = (".env", ".env.local")
DOCKER_ENV_FILE_NAMES = (".env", ".env.docker")


def _sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


DEFAULT_DATABASE_URL = _sqlite_url(DATA_ROOT / "fe_local.db")
DEFAULT_DOCS_ROOT = str(DATA_ROOT / "asx" / "docs")
DEFAULT_MARKETINDEX_ANNOUNCEMENTS_FILE = str(DATA_ROOT / "raw" / "marketindex_announcements.json")
DEFAULT_IMPORTANCE_OUTPUT_ROOT = str(DATA_ROOT / "asx" / "importance")


def _resolve_env_file_paths(*env_file_names: str) -> tuple[Path, ...]:
    return tuple((PROJECT_ROOT / env_file_name).resolve() for env_file_name in env_file_names)


def is_running_in_docker() -> bool:
    if Path("/.dockerenv").exists():
        return True
    cgroup_path = Path("/proc/1/cgroup")
    try:
        cgroup_text = cgroup_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return any(marker in cgroup_text for marker in ("docker", "containerd", "kubepods", "podman"))


def _running_in_docker() -> bool:
    return is_running_in_docker()


def _host_network_enabled() -> bool:
    value = str(os.getenv("TENN_HOST_NETWORK", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _select_runtime_env_files() -> tuple[Path, ...]:
    docker_env_files = _resolve_env_file_paths(*DOCKER_ENV_FILE_NAMES)
    if _running_in_docker() and len(docker_env_files) > 1 and docker_env_files[1].exists():
        return docker_env_files
    return _resolve_env_file_paths(*DEFAULT_ENV_FILE_NAMES)


def _loaded_env_file_names(env_files: tuple[Path, ...]) -> tuple[str, ...]:
    return tuple(path.name for path in env_files if path.exists())


def _using_local_baseline(env_files: tuple[Path, ...]) -> bool:
    return _loaded_env_file_names(env_files) == DEFAULT_ENV_FILE_NAMES


def _model_routing_config_path_from_module_path(module_path: Path) -> Path:
    return module_path.resolve().parents[1] / "config" / "model_routing.yaml"


def _resolve_project_path(value: str) -> str:
    p = Path(str(value or "")).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return str(p)


def _shell_override_present(name: str) -> bool:
    return name in os.environ


def _normalize_base_url(url: str, *, default: str, strip_v1: bool = False) -> str:
    text = str(url or "").strip() or str(default).strip()
    normalized = text.rstrip("/")
    if strip_v1 and normalized.endswith("/v1"):
        normalized = normalized[: -len("/v1")]
    return normalized.rstrip("/")


def _extract_host_port(url: str) -> tuple[str, int | None]:
    normalized = _normalize_base_url(url, default="", strip_v1=True)
    parsed = urlparse(normalized)
    return str(parsed.hostname or "").strip().lower(), parsed.port


def validate_llm_endpoints(llamacpp_url: str, ollama_url: str) -> None:
    normalized_llamacpp = _normalize_base_url(
        llamacpp_url,
        default="",
        strip_v1=True,
    )
    normalized_ollama = _normalize_base_url(
        ollama_url,
        default="",
        strip_v1=True,
    )
    if not normalized_llamacpp:
        raise ValueError("LLAMACPP_URL must be set")
    if not normalized_ollama:
        return
    llamacpp_host, llamacpp_port = _extract_host_port(normalized_llamacpp)
    ollama_host, ollama_port = _extract_host_port(normalized_ollama)
    if normalized_llamacpp == normalized_ollama or (
        llamacpp_host
        and ollama_host
        and llamacpp_host == ollama_host
        and llamacpp_port == ollama_port
    ):
        raise RuntimeError(
            "Invalid configuration: LLAMACPP_URL and OLLAMA_URL resolve to the same host:port. "
            "This causes backend aliasing."
        )


def _normalize_database_url(url: str) -> str:
    text = str(url or "").strip()
    lowered = text.lower()
    if not lowered.startswith("sqlite:///"):
        parsed = urlparse(text)
        if parsed.scheme not in {
            "postgresql",
            "postgresql+psycopg",
            "postgresql+psycopg2",
            "postgresql+asyncpg",
        }:
            return text
        hostname = str(parsed.hostname or "").strip().lower()
        if hostname not in {"", "postgres", "127.0.0.1", "localhost"}:
            return text

        runtime_hostname = "postgres" if is_running_in_docker() and not _host_network_enabled() else "127.0.0.1"
        rewritten_netloc = runtime_hostname
        if parsed.port is not None:
            rewritten_netloc = f"{rewritten_netloc}:{parsed.port}"
        if parsed.username:
            credentials = parsed.username
            if parsed.password is not None:
                credentials = f"{credentials}:{parsed.password}"
            rewritten_netloc = f"{credentials}@{rewritten_netloc}"
        return urlunparse(parsed._replace(netloc=rewritten_netloc))

    raw_path = text[len("sqlite:///") :]
    if raw_path in {"", ":memory:"} or raw_path.startswith("file:"):
        return text
    p = Path(raw_path).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return _sqlite_url(p)


def _default_redis_base_url() -> str:
    host = "redis" if is_running_in_docker() else "127.0.0.1"
    return f"redis://{host}:6379"


def _normalize_redis_url(url: str, *, default_db: int = 0) -> str:
    text = str(url or "").strip()
    if not text:
        return f"{_default_redis_base_url()}/{default_db}"
    if "://" not in text and ":" in text:
        text = f"redis://{text}"

    parsed = urlparse(text)
    hostname = str(parsed.hostname or "").strip().lower()
    if parsed.scheme not in {"redis", "rediss"}:
        return text

    runtime_hostname = "redis" if is_running_in_docker() and not _host_network_enabled() else "127.0.0.1"
    if hostname not in {"", "redis", "127.0.0.1", "localhost"}:
        return text

    rewritten_netloc = runtime_hostname
    if parsed.port is not None:
        rewritten_netloc = f"{rewritten_netloc}:{parsed.port}"
    if parsed.username:
        credentials = parsed.username
        if parsed.password is not None:
            credentials = f"{credentials}:{parsed.password}"
        rewritten_netloc = f"{credentials}@{rewritten_netloc}"

    rewritten_path = parsed.path or f"/{default_db}"
    return urlunparse(parsed._replace(netloc=rewritten_netloc, path=rewritten_path))


def _normalize_qdrant_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return "http://127.0.0.1:6333"
    if "://" not in text and text.lower().startswith("qdrant:"):
        text = f"http://{text}"

    parsed = urlparse(text)
    hostname = str(parsed.hostname or "").strip().lower()
    if hostname != "qdrant":
        return text
    if _running_in_docker() and not _host_network_enabled():
        return text

    rewritten_netloc = "127.0.0.1"
    if parsed.port is not None:
        rewritten_netloc = f"{rewritten_netloc}:{parsed.port}"
    if parsed.username:
        credentials = parsed.username
        if parsed.password is not None:
            credentials = f"{credentials}:{parsed.password}"
        rewritten_netloc = f"{credentials}@{rewritten_netloc}"

    return urlunparse(parsed._replace(netloc=rewritten_netloc))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILE_NAMES,
        extra="ignore",
        protected_namespaces=("settings_", "model_"),
    )

    app_env: str = "dev"
    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = f"{_default_redis_base_url()}/0"
    celery_broker_url: str = f"{_default_redis_base_url()}/0"
    celery_result_backend: str = f"{_default_redis_base_url()}/1"
    local_api_key: str = ""
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_timeout_seconds: int = 60
    qdrant_collection: str = "asx_docs"
    data_root: str = str(DATA_ROOT)
    docs_root: str = DEFAULT_DOCS_ROOT
    ollama_url: str = ""
    llamacpp_url: str = "http://127.0.0.1:8001"
    extraction_llamacpp_url: str = ""
    llamacpp_timeout_seconds: float = 120.0
    model_routing_config: str = str(_model_routing_config_path_from_module_path(Path(__file__)))
    embed_model: str = "nomic-embed-text"
    embedding_batch_size: int = 32
    extract_model: str = "qwen2.5-14b-instruct"
    gpu_utilization_threshold: int = 95
    gpu_utilization_command: str = "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits"
    routing_short_prompt_chars: int = 400
    routing_long_context_chars: int = 12000
    backfill_concurrency: int = 1

    task_mode: str = "celery"
    auto_create_tables: bool = False
    enable_embeddings: bool = True
    enable_embedding_cache: bool = False
    enable_qdrant: bool = True
    enable_extraction: bool = True
    enable_marketindex_fallback: bool = False
    marketindex_announcements_file: str = DEFAULT_MARKETINDEX_ANNOUNCEMENTS_FILE
    enable_importance_classification: bool = True
    importance_output_root: str = DEFAULT_IMPORTANCE_OUTPUT_ROOT
    importance_materialize_output: bool = False
    importance_include_pdf_text: bool = True
    importance_link_mode: str = "symlink"
    importance_sort_source_docs: bool = True
    router_feedback_enabled: bool = True
    analyzer_max_age_seconds: int = 600
    market_data_mode: str = "yahoo"
    market_data_base_url: str = "https://query1.finance.yahoo.com"
    market_data_timeout_seconds: float = 20.0
    openbb_sidecar_base_url: str = "http://127.0.0.1:8081"
    openbb_sidecar_timeout_seconds: float = 15.0
    openbb_sidecar_enable_staging_writes: bool = False
    enable_session_memory: bool = True


def _validate_runtime_configuration(current_settings: Settings, env_files: tuple[Path, ...]) -> None:
    if not _using_local_baseline(env_files):
        return
    if current_settings.task_mode != "sync" or not current_settings.enable_embeddings:
        return


RUNTIME_ENV_FILES = _select_runtime_env_files()
LOADED_ENV_FILES = _loaded_env_file_names(RUNTIME_ENV_FILES)

settings = Settings(_env_file=tuple(str(path) for path in RUNTIME_ENV_FILES))
settings.data_root = _resolve_project_path(settings.data_root or "./data")
if (
    not _shell_override_present("DATABASE_URL")
    and (not str(settings.database_url or "").strip() or settings.database_url == DEFAULT_DATABASE_URL)
):
    settings.database_url = _sqlite_url(Path(settings.data_root) / "fe_local.db")
if (
    not _shell_override_present("DOCS_ROOT")
    and (not str(settings.docs_root or "").strip() or settings.docs_root == DEFAULT_DOCS_ROOT)
):
    settings.docs_root = str(Path(settings.data_root) / "asx" / "docs")
if (
    not _shell_override_present("MARKETINDEX_ANNOUNCEMENTS_FILE")
    and (
        not str(settings.marketindex_announcements_file or "").strip()
        or settings.marketindex_announcements_file == DEFAULT_MARKETINDEX_ANNOUNCEMENTS_FILE
    )
):
    settings.marketindex_announcements_file = str(Path(settings.data_root) / "raw" / "marketindex_announcements.json")
if (
    not _shell_override_present("IMPORTANCE_OUTPUT_ROOT")
    and (
        not str(settings.importance_output_root or "").strip()
        or settings.importance_output_root == DEFAULT_IMPORTANCE_OUTPUT_ROOT
    )
):
    settings.importance_output_root = str(Path(settings.data_root) / "asx" / "importance")
settings.database_url = _normalize_database_url(settings.database_url)
settings.qdrant_url = _normalize_base_url(
    _normalize_qdrant_url(settings.qdrant_url),
    default="http://127.0.0.1:6333",
)
settings.redis_url = _normalize_redis_url(settings.redis_url, default_db=0)
settings.celery_broker_url = _normalize_redis_url(
    settings.celery_broker_url or settings.redis_url,
    default_db=0,
)
settings.celery_result_backend = _normalize_redis_url(
    settings.celery_result_backend or settings.redis_url,
    default_db=1,
)
settings.docs_root = _resolve_project_path(settings.docs_root)
settings.marketindex_announcements_file = _resolve_project_path(settings.marketindex_announcements_file)
settings.importance_output_root = _resolve_project_path(settings.importance_output_root)
settings.model_routing_config = _resolve_project_path(settings.model_routing_config)
settings.ollama_url = _normalize_base_url(settings.ollama_url, default="", strip_v1=True)
settings.llamacpp_url = _normalize_base_url(
    settings.llamacpp_url,
    default="http://127.0.0.1:8001",
    strip_v1=True,
)
settings.extraction_llamacpp_url = _normalize_base_url(
    settings.extraction_llamacpp_url,
    default="",
    strip_v1=True,
)
validate_llm_endpoints(
    settings.llamacpp_url,
    settings.ollama_url,
)
_validate_runtime_configuration(settings, RUNTIME_ENV_FILES)
