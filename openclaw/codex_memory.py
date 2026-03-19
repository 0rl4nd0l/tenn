from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
from typing import Any


MAX_BOOTSTRAP_CHARS = 12_000
MAX_SECTION_CHARS = 2_500
MAX_SEARCH_RESULTS = 50
MAX_RECALL_CHARS = 8_000
MAX_SESSION_LOOKUP_RESULTS = 200


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    return collapsed.strip("-") or "session"


def _trim_text(value: str, *, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    clipped = text[: max(0, limit - 3)].rstrip()
    return f"{clipped}..."


class CodexMemoryStore:
    """Repo-local Codex memory with an OpenViking-aligned path shape."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def build_bootstrap(
        self,
        *,
        recent_sessions: int = 5,
        include_daily_notes: bool = True,
        include_digest: bool = True,
    ) -> dict[str, Any]:
        if recent_sessions < 1 or recent_sessions > 20:
            raise ValueError("recent_sessions must be between 1 and 20")

        user_path = self.repo_root / "USER.md"
        durable_path = self.repo_root / "MEMORY.md"
        digest_path = self.repo_root / "reports" / "agent_context_digest.md"

        sessions = self.list_sessions(limit=recent_sessions)
        daily_notes = self._recent_daily_notes(limit=2 if include_daily_notes else 0)

        sections: list[str] = []
        structured: dict[str, Any] = {
            "user_path": user_path.relative_to(self.repo_root).as_posix(),
            "memory_path": durable_path.relative_to(self.repo_root).as_posix(),
            "daily_notes": daily_notes,
            "sessions": sessions,
            "openviking_root": "viking://tenn/codex",
        }

        user_text = self._read_optional_text(user_path)
        if user_text:
            sections.append(self._render_section("USER.md", user_text))

        durable_text = self._read_optional_text(durable_path)
        if durable_text:
            sections.append(self._render_section("MEMORY.md", durable_text))

        if daily_notes:
            blocks = []
            for entry in daily_notes:
                blocks.append(f"### {entry['path']}\n{entry['excerpt']}")
            sections.append(self._render_section("Recent Daily Notes", "\n\n".join(blocks)))

        if sessions:
            blocks = []
            for entry in sessions:
                body = _trim_text(str(entry.get("summary", "")), limit=1_000)
                blocks.append(f"### {entry['title']} ({entry['path']})\n{body}")
            sections.append(self._render_section("Recent Codex Sessions", "\n\n".join(blocks)))

        if include_digest:
            digest_text = self._read_optional_text(digest_path)
            if digest_text:
                structured["digest_path"] = digest_path.relative_to(self.repo_root).as_posix()
                sections.append(self._render_section("Agent Context Digest", digest_text))

        text = "\n\n".join(part for part in sections if part).strip()
        return {
            "text": _trim_text(text, limit=MAX_BOOTSTRAP_CHARS) or "No Codex memory files found.",
            "structured": structured,
        }

    def search(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        needle = query.strip()
        if not needle:
            raise ValueError("query is required")
        if limit < 1 or limit > MAX_SEARCH_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_SEARCH_RESULTS}")

        lowered = needle.casefold()
        matches: list[dict[str, Any]] = []
        for path in self._search_paths():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                line_text = line.strip()
                if lowered not in line_text.casefold():
                    continue
                matches.append(
                    {
                        "path": path.relative_to(self.repo_root).as_posix(),
                        "line": line_number,
                        "text": _trim_text(line_text, limit=240),
                    }
                )
                if len(matches) >= limit:
                    return matches
        return matches

    def list_sessions(self, *, limit: int = 10) -> list[dict[str, Any]]:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        session_files = self._session_files()
        return [self._read_session_entry(path) for path in session_files[:limit]]

    def get_session(self, session_ref: str) -> dict[str, Any]:
        normalized_ref = session_ref.strip()
        if not normalized_ref:
            raise ValueError("session_ref is required")

        exact_path = (self.repo_root / normalized_ref).resolve()
        try:
            exact_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("Requested path is outside the Tenn repository.") from exc

        session_files = self._session_files()
        if not session_files:
            raise FileNotFoundError("No Codex session summaries found.")

        if normalized_ref == "latest":
            path = session_files[0]
            return self._read_session_document(path)

        if exact_path.is_file():
            session_root = self._session_root()
            if not exact_path.is_relative_to(session_root):
                raise ValueError("Requested path is not a Codex session summary.")
            return self._read_session_document(exact_path)

        matches: list[Path] = []
        for path in session_files[:MAX_SESSION_LOOKUP_RESULTS]:
            entry = self._read_session_entry(path)
            identifiers = {
                entry["path"],
                entry["openviking_path"],
                path.name,
                path.stem,
            }
            if normalized_ref in identifiers:
                matches.append(path)
        if not matches:
            raise FileNotFoundError(f"Codex session not found: {normalized_ref}")
        if len(matches) > 1:
            raise ValueError(f"Multiple Codex sessions match {normalized_ref!r}; use the full path.")
        return self._read_session_document(matches[0])

    def build_recall(self, query: str, *, limit: int = 5, max_chars: int = 4_000) -> dict[str, Any]:
        needle = query.strip()
        if not needle:
            raise ValueError("query is required")
        if limit < 1 or limit > 10:
            raise ValueError("limit must be between 1 and 10")
        if max_chars < 500 or max_chars > MAX_RECALL_CHARS:
            raise ValueError(f"max_chars must be between 500 and {MAX_RECALL_CHARS}")

        matches = self.search(needle, limit=min(MAX_SEARCH_RESULTS, limit * 5))
        deduped_paths: list[Path] = []
        seen_paths: set[str] = set()
        for match in matches:
            relative_path = str(match["path"])
            if relative_path in seen_paths:
                continue
            candidate = self.repo_root / relative_path
            if not candidate.is_file():
                continue
            deduped_paths.append(candidate)
            seen_paths.add(relative_path)
            if len(deduped_paths) >= limit:
                break

        entries: list[dict[str, Any]] = []
        rendered_blocks: list[str] = []
        remaining_chars = max_chars
        for path in deduped_paths:
            entry = self._build_recall_entry(path, needle, remaining_chars)
            if entry is None:
                continue
            entries.append(entry)
            block = f"## {entry['title']} ({entry['path']})\n{entry['excerpt']}".strip()
            block = _trim_text(block, limit=max(200, remaining_chars))
            rendered_blocks.append(block)
            remaining_chars -= len(block) + 2
            if remaining_chars <= 200:
                break

        text = "\n\n".join(rendered_blocks).strip()
        if not text:
            text = f"No Codex memory recall results for {needle!r}."
        return {
            "text": _trim_text(text, limit=max_chars),
            "structured": {
                "query": needle,
                "matches": matches,
                "entries": entries,
            },
        }

    def write_session_summary(
        self,
        *,
        summary: str,
        title: str = "",
        tags: list[str] | None = None,
        source_paths: list[str] | None = None,
        outcome: str = "",
    ) -> dict[str, Any]:
        body = summary.strip()
        if not body:
            raise ValueError("summary is required")

        normalized_title = title.strip() or body.splitlines()[0].strip()
        session_title = normalized_title[:120] or "Codex session"
        session_slug = _slugify(session_title)[:48]
        cleaned_tags = sorted({item.strip() for item in tags or [] if item and item.strip()})
        cleaned_sources = [item.strip() for item in source_paths or [] if item and item.strip()]
        normalized_outcome = outcome.strip()

        now = datetime.now().astimezone()
        date_dir = now.strftime("%Y-%m-%d")
        time_part = now.strftime("%H%M%S%f")
        file_name = f"{time_part}-{session_slug}.md"
        relative_path = Path("memory") / "codex" / "sessions" / date_dir / file_name
        absolute_path = self.repo_root / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        viking_path = (
            f"viking://tenn/codex/sessions/{now.strftime('%Y/%m/%d')}/{time_part}-{session_slug}"
        )
        absolute_path.write_text(
            self._render_session_markdown(
                title=session_title,
                created_at=now.isoformat(),
                outcome=normalized_outcome,
                tags=cleaned_tags,
                source_paths=cleaned_sources,
                openviking_path=viking_path,
                summary=body,
            ),
            encoding="utf-8",
        )

        return {
            "path": relative_path.as_posix(),
            "title": session_title,
            "created_at": now.isoformat(),
            "outcome": normalized_outcome,
            "tags": cleaned_tags,
            "source_paths": cleaned_sources,
            "openviking_path": viking_path,
            "summary": _trim_text(body, limit=1_000),
        }

    def _recent_daily_notes(self, *, limit: int) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        memory_root = self.repo_root / "memory"
        candidates = sorted(memory_root.glob("*.md"), reverse=True)
        notes: list[dict[str, Any]] = []
        for path in candidates[:limit]:
            text = self._read_optional_text(path)
            if not text:
                continue
            notes.append(
                {
                    "path": path.relative_to(self.repo_root).as_posix(),
                    "excerpt": _trim_text(text, limit=MAX_SECTION_CHARS),
                }
            )
        return notes

    def _search_paths(self) -> list[Path]:
        paths: list[Path] = []
        for candidate in (
            self.repo_root / "USER.md",
            self.repo_root / "MEMORY.md",
            self.repo_root / "reports" / "agent_context_digest.md",
        ):
            if candidate.is_file():
                paths.append(candidate)

        memory_root = self.repo_root / "memory"
        if memory_root.exists():
            paths.extend(sorted(memory_root.glob("*.md"), reverse=True))

        session_root = self._session_root()
        if session_root.exists():
            paths.extend(self._session_files())
        return paths

    def _session_root(self) -> Path:
        return self.repo_root / "memory" / "codex" / "sessions"

    def _session_files(self) -> list[Path]:
        session_root = self._session_root()
        if not session_root.exists():
            return []
        return sorted(session_root.rglob("*.md"), reverse=True)

    def _read_optional_text(self, path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    def _render_section(self, heading: str, body: str) -> str:
        trimmed = _trim_text(body, limit=MAX_SECTION_CHARS)
        return f"## {heading}\n{trimmed}".strip()

    def _render_session_markdown(
        self,
        *,
        title: str,
        created_at: str,
        outcome: str,
        tags: list[str],
        source_paths: list[str],
        openviking_path: str,
        summary: str,
    ) -> str:
        lines = [
            "# Codex Session Summary",
            "",
            f"- title: {title}",
            f"- created_at: {created_at}",
            f"- outcome: {outcome or 'unspecified'}",
            f"- openviking_path: {openviking_path}",
            f"- tags: {', '.join(tags) if tags else 'none'}",
            "- source_paths:",
        ]
        if source_paths:
            lines.extend([f"  - {item}" for item in source_paths])
        else:
            lines.append("  - none")
        lines.extend(("", "## Summary", summary.strip(), ""))
        return "\n".join(lines)

    def _read_session_entry(self, path: Path) -> dict[str, Any]:
        raw = path.read_text(encoding="utf-8")
        title = path.stem
        created_at = ""
        outcome = ""
        openviking_path = ""
        tags: list[str] = []
        source_paths: list[str] = []
        summary = raw.strip()
        in_sources = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped == "## Summary":
                _, _, tail = raw.partition("## Summary")
                summary = tail.strip()
                break
            if stripped.startswith("- title:"):
                title = stripped.removeprefix("- title:").strip() or title
                in_sources = False
            elif stripped.startswith("- created_at:"):
                created_at = stripped.removeprefix("- created_at:").strip()
                in_sources = False
            elif stripped.startswith("- outcome:"):
                outcome = stripped.removeprefix("- outcome:").strip()
                in_sources = False
            elif stripped.startswith("- openviking_path:"):
                openviking_path = stripped.removeprefix("- openviking_path:").strip()
                in_sources = False
            elif stripped.startswith("- tags:"):
                tag_text = stripped.removeprefix("- tags:").strip()
                tags = [] if tag_text in {"", "none"} else [item.strip() for item in tag_text.split(",") if item.strip()]
                in_sources = False
            elif stripped == "- source_paths:":
                in_sources = True
            elif in_sources and stripped.startswith("- "):
                source_value = stripped.removeprefix("- ").strip()
                if source_value and source_value != "none":
                    source_paths.append(source_value)
            elif stripped and not stripped.startswith("- "):
                in_sources = False

        return {
            "path": path.relative_to(self.repo_root).as_posix(),
            "title": title,
            "created_at": created_at,
            "outcome": outcome,
            "openviking_path": openviking_path,
            "tags": tags,
            "source_paths": source_paths,
            "summary": _trim_text(summary, limit=1_500),
        }

    def _read_session_document(self, path: Path) -> dict[str, Any]:
        markdown = path.read_text(encoding="utf-8")
        entry = self._read_session_entry(path)
        return {
            "session": entry,
            "markdown": markdown,
        }

    def _build_recall_entry(self, path: Path, query: str, remaining_chars: int) -> dict[str, Any] | None:
        raw = self._read_optional_text(path)
        if not raw:
            return None
        session_root = self._session_root()
        excerpt_limit = max(300, min(1_200, remaining_chars))
        excerpt = self._excerpt_for_query(raw, query, limit=excerpt_limit)
        if path.is_relative_to(session_root):
            entry = self._read_session_entry(path)
            return {
                "path": entry["path"],
                "title": entry["title"],
                "openviking_path": entry["openviking_path"],
                "excerpt": excerpt,
            }
        return {
            "path": path.relative_to(self.repo_root).as_posix(),
            "title": path.name,
            "openviking_path": "",
            "excerpt": excerpt,
        }

    def _excerpt_for_query(self, text: str, query: str, *, limit: int) -> str:
        lines = text.splitlines()
        lowered = query.casefold()
        match_index = 0
        for index, line in enumerate(lines):
            if lowered in line.casefold():
                match_index = index
                break
        start = max(0, match_index - 3)
        end = min(len(lines), match_index + 4)
        excerpt = "\n".join(lines[start:end]).strip()
        if not excerpt:
            excerpt = text.strip()
        return _trim_text(excerpt, limit=limit)
