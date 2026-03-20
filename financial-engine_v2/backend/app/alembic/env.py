import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure `app.*` imports resolve regardless of current working directory.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models import Base

config = context.config
target_metadata = Base.metadata


def _running_in_docker() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup_text = Path("/proc/1/cgroup").read_text(encoding="utf-8")
    except OSError:
        return False
    return any(marker in cgroup_text for marker in ("docker", "containerd", "kubepods", "podman"))


def _host_network_enabled() -> bool:
    value = str(os.getenv("TENN_HOST_NETWORK", "")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _normalize_database_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in {
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
        "postgresql+asyncpg",
    }:
        return url

    hostname = str(parsed.hostname or "").strip().lower()
    if hostname not in {"", "postgres", "127.0.0.1", "localhost"}:
        return url

    runtime_hostname = "postgres" if _running_in_docker() and not _host_network_enabled() else "127.0.0.1"
    rewritten_netloc = runtime_hostname
    if parsed.port is not None:
        rewritten_netloc = f"{rewritten_netloc}:{parsed.port}"
    if parsed.username:
        credentials = parsed.username
        if parsed.password is not None:
            credentials = f"{credentials}:{parsed.password}"
        rewritten_netloc = f"{credentials}@{rewritten_netloc}"
    return urlunparse(parsed._replace(netloc=rewritten_netloc))


def get_url():
    return _normalize_database_url(os.environ["DATABASE_URL"])
def run_migrations_offline():
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
