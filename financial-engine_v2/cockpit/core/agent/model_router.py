"""
Per-function model router for the cockpit agent system.

Loads role-to-model mappings from ~/.tenn/config/model_routing.yaml (if present),
with env var defaults for unset roles.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Ordered list of known roles — order is not significant for routing, but
# defines the canonical set used for validation.
KNOWN_ROLES: tuple[str, ...] = (
    "orchestrator",
    "analyst",
    "subagent",
    "deep_reasoning",
    "coder",
    "extraction",
)

_DEFAULT_CONFIG_PATH = Path.home() / ".tenn" / "config" / "model_routing.yaml"


def _env(key: str, fallback: str = "") -> str:
    return os.environ.get(key, fallback)


def _build_defaults() -> dict[str, str]:
    """Return role defaults resolved from environment variables."""
    chat_model = _env("LLAMACPP_CHAT_MODEL", "")
    return {
        "orchestrator": chat_model,
        "analyst": chat_model,
        "subagent": "",
        "deep_reasoning": "",
        "coder": "",
        "extraction": _env("EXTRACT_MODEL", "qwen2.5-14b-instruct"),
    }


def _load_yaml_file(path: Path) -> dict[str, str]:
    """
    Attempt to load a YAML file and return a str→str dict.

    Returns an empty dict if the file cannot be parsed or pyyaml is absent.
    Emits a warning in either failure case.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "pyyaml is not installed; model_routing.yaml will be ignored. "
            "Install pyyaml to enable config-file overrides."
        )
        return {}

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse %s: %s — using defaults.", path, exc)
        return {}

    if not isinstance(raw, dict):
        logger.warning(
            "%s did not parse to a mapping (got %s) — using defaults.",
            path,
            type(raw).__name__,
        )
        return {}

    # Coerce all values to str; skip non-str keys or non-str-convertible values.
    result: dict[str, str] = {}
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        result[k] = str(v) if v is not None else ""
    return result


class ModelRouter:
    """
    Maps agent roles to model names.

    Resolution order for each role:
      1. Explicit update() call (runtime override)
      2. ~/.tenn/config/model_routing.yaml (if present and parseable)
      3. Env var defaults (LLAMACPP_CHAT_MODEL / EXTRACT_MODEL)
      4. Empty string → treated as unset by model_for()
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config_path: Path = config_path or _DEFAULT_CONFIG_PATH
        self._routing: dict[str, str] = self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, str]:
        routing = _build_defaults()

        if self._config_path.exists():
            file_overrides = _load_yaml_file(self._config_path)
            for role, model in file_overrides.items():
                if role in KNOWN_ROLES:
                    routing[role] = model
                else:
                    logger.warning(
                        "model_routing.yaml contains unknown role %r — ignoring.",
                        role,
                    )
        return routing

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def model_for(self, role: str) -> Optional[str]:
        """
        Return the model name for *role*, or None if the role is unset or empty.

        Unknown roles return None without raising.
        """
        value = self._routing.get(role, "")
        return value if value else None

    def update(self, role: str, model_name: str) -> None:
        """
        Override the model for *role* at runtime.

        Raises ValueError for roles not in KNOWN_ROLES.
        """
        if role not in KNOWN_ROLES:
            raise ValueError(
                f"Unknown role {role!r}. Known roles: {', '.join(KNOWN_ROLES)}"
            )
        self._routing[role] = model_name

    def as_dict(self) -> dict[str, str]:
        """Return a copy of the current role→model mapping."""
        return dict(self._routing)
