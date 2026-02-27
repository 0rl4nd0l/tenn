from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any


class FileIndexer:
    CACHE_TTL_SECONDS = 8.0
    MAX_SEARCH_CACHE = 64

    def __init__(self, roots: list[str], default_root: str | Path | None = None) -> None:
        expanded = [Path(p).expanduser().resolve() for p in roots]
        self.default_root = Path(default_root).expanduser().resolve() if default_root else None
        home = Path.home().resolve()
        broad_roots = {Path("/"), home, home.parent}

        filtered: list[Path] = []
        for root in expanded:
            if not root.exists():
                continue
            # Broad roots ("/" or user home) can make every chat turn expensive.
            if root in broad_roots:
                continue
            filtered.append(root)

        if not filtered and self.default_root and self.default_root.exists():
            filtered = [self.default_root]

        self.roots = filtered
        self._reports_cache: tuple[float, list[str]] | None = None
        self._search_cache: dict[tuple[str, int], tuple[float, list[dict[str, Any]]]] = {}

    def list_recent_reports(self, limit: int = 20) -> list[str]:
        now = time.monotonic()
        if self._reports_cache:
            cached_at, cached_rows = self._reports_cache
            if now - cached_at <= self.CACHE_TTL_SECONDS:
                return cached_rows[:limit]

        files: list[Path] = []
        for root in self.roots:
            reports = root / "reports"
            if reports.exists():
                files.extend([p for p in reports.rglob("*.json") if p.is_file()])
                files.extend([p for p in reports.rglob("*.md") if p.is_file()])
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        rows = [str(p) for p in files]
        self._reports_cache = (now, rows)
        return rows[:limit]

    def search_text(self, pattern: str, limit: int = 50) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        query = pattern.strip()
        if not query:
            return results

        key = (query, limit)
        now = time.monotonic()
        cached = self._search_cache.get(key)
        if cached and now - cached[0] <= self.CACHE_TTL_SECONDS:
            return cached[1]

        for root in self.roots:
            remaining = limit - len(results)
            if remaining <= 0:
                break
            cmd = [
                "rg",
                "-n",
                "--fixed-strings",
                "-m",
                str(remaining),
                "--max-filesize",
                "2M",
                "--glob",
                "!**/.git/**",
                "--glob",
                "!**/.venv/**",
                "--glob",
                "!**/__pycache__/**",
                query,
                str(root),
            ]
            try:
                output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
            except Exception:
                continue
            for line in output.splitlines():
                if len(results) >= limit:
                    break
                parts = line.split(":", 2)
                if len(parts) != 3:
                    continue
                path, line_no, text_value = parts
                results.append({"path": path, "line": line_no, "text": text_value.strip()})

        if len(self._search_cache) >= self.MAX_SEARCH_CACHE:
            oldest_key = min(self._search_cache.items(), key=lambda item: item[1][0])[0]
            self._search_cache.pop(oldest_key, None)
        self._search_cache[key] = (now, results)
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
