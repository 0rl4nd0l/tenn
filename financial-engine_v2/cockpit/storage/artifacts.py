from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, repo_root: Path, exports_dir: str, reports_dir: str) -> None:
        self.repo_root = repo_root
        self.exports_dir = (repo_root / exports_dir).resolve()
        self.reports_dir = (repo_root / reports_dir).resolve()
        self.logs_dir = (self.reports_dir / "cockpit" / "logs").resolve()
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def write_json(self, rel_path: str, payload: dict[str, Any]) -> str:
        path = (self.repo_root / rel_path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def write_analysis(self, thread_id: str, question: str, answer: str, payload: dict[str, Any]) -> tuple[str, str]:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base = self.exports_dir / thread_id
        base.mkdir(parents=True, exist_ok=True)

        md_path = base / f"{ts}.md"
        json_path = base / f"{ts}.json"

        md_path.write_text(
            f"# Analysis\n\n## Question\n{question}\n\n## Answer\n{answer}\n",
            encoding="utf-8",
        )
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(md_path), str(json_path)
