from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class FileIndexer:
    def __init__(self, roots: list[str]) -> None:
        expanded = [Path(p).expanduser().resolve() for p in roots]
        self.roots = [p for p in expanded if p.exists()]

    def list_recent_reports(self, limit: int = 20) -> list[str]:
        files: list[Path] = []
        for root in self.roots:
            reports = root / "reports"
            if reports.exists():
                files.extend([p for p in reports.rglob("*.json") if p.is_file()])
                files.extend([p for p in reports.rglob("*.md") if p.is_file()])
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [str(p) for p in files[:limit]]

    # Subdirectories searched per root; intentionally narrow to avoid scanning
    # the full home directory on every chat message.
    _SEARCH_SUBDIRS = ("reports", "data")

    def search_text(self, pattern: str, limit: int = 50) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if not pattern.strip():
            return results
        for root in self.roots:
            search_dirs = [root / sub for sub in self._SEARCH_SUBDIRS if (root / sub).is_dir()]
            if not search_dirs:
                continue
            cmd = [
                "rg", "-n", "-m", str(limit),
                "--max-filesize", "1M",
                "--max-depth", "6",
                pattern,
                *[str(d) for d in search_dirs],
            ]
            try:
                output = subprocess.check_output(
                    cmd, text=True, stderr=subprocess.DEVNULL, timeout=5
                )
            except subprocess.TimeoutExpired:
                continue
            except Exception:
                continue
            for line in output.splitlines():
                if len(results) >= limit:
                    return results
                if ":" not in line:
                    continue
                path, rest = line.split(":", 1)
                line_no, _, text_value = rest.partition(":")
                results.append({"path": path, "line": line_no, "text": text_value.strip()})
        return results

    def is_allowed_path(self, path: str) -> bool:
        target = Path(path).expanduser().resolve()
        for root in self.roots:
            try:
                target.relative_to(root)
                return True
            except Exception:
                continue
        return False

    def read_file(self, path: str, max_chars: int = 16000) -> dict[str, Any]:
        target = Path(path).expanduser().resolve()
        if not self.is_allowed_path(str(target)):
            return {
                "ok": False,
                "error": f"path not allowed: {target}",
                "path": str(target),
            }
        if not target.exists() or not target.is_file():
            return {
                "ok": False,
                "error": "file not found",
                "path": str(target),
            }

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {
                "ok": False,
                "error": f"read failed: {exc}",
                "path": str(target),
            }

        clipped = content[:max_chars]
        return {
            "ok": True,
            "path": str(target),
            "chars_total": len(content),
            "chars_returned": len(clipped),
            "truncated": len(content) > len(clipped),
            "content": clipped,
        }
