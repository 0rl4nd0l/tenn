from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FINANCIAL_ENGINE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CHANNEL_REGISTRY_PATH = FINANCIAL_ENGINE_ROOT / "channel_registry.json"


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    channel_id: str
    credibility_weight: float = 0.55
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "channel_id": self.channel_id,
            "credibility_weight": self.credibility_weight,
            "enabled": self.enabled,
        }


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() not in {"", "0", "false", "no", "off"}


class ChannelRegistry:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or DEFAULT_CHANNEL_REGISTRY_PATH).expanduser().resolve()

    def ensure_exists(self) -> Path:
        if self.path.exists():
            return self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"channels": []}, indent=2) + "\n", encoding="utf-8")
        return self.path

    def load(self) -> dict[str, Any]:
        self.ensure_exists()
        payload = json.loads(self.path.read_text(encoding="utf-8") or "{}")
        if not isinstance(payload, dict):
            raise RuntimeError("channel registry must be a JSON object")
        channels = payload.get("channels", [])
        if not isinstance(channels, list):
            raise RuntimeError("channel registry channels must be a list")
        return payload

    def channels(self) -> list[ChannelConfig]:
        payload = self.load()
        rows = payload.get("channels") or []
        parsed: list[ChannelConfig] = []
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("channel registry rows must be JSON objects")
            channel_id = str(row.get("channel_id") or "").strip()
            name = str(row.get("name") or channel_id).strip() or channel_id
            if not channel_id:
                raise RuntimeError("channel registry rows require channel_id")
            credibility_weight = row.get("credibility_weight")
            if credibility_weight in (None, ""):
                credibility_weight = 0.55
            parsed.append(
                ChannelConfig(
                    name=name,
                    channel_id=channel_id,
                    credibility_weight=float(credibility_weight),
                    enabled=_coerce_bool(row.get("enabled", True)),
                )
            )
        return parsed

    def enabled_channels(self) -> list[ChannelConfig]:
        return [channel for channel in self.channels() if channel.enabled]

    def save(self, channels: list[ChannelConfig]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"channels": [channel.to_dict() for channel in channels]}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
