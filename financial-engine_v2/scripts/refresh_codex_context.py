#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path.home() / ".codex" / "config.toml"
DEFAULT_DIGEST_PATH = REPO_ROOT / "reports" / "agent_context_digest.md"
DEFAULT_STATE_PATH = REPO_ROOT / "reports" / "agent_context_snapshot.json"
BEGIN_MARKER = "# BEGIN TENN_AGENT_CONTEXT"
END_MARKER = "# END TENN_AGENT_CONTEXT"


def _run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return (completed.stdout or "").strip()


def _changed_files_workspace() -> list[str]:
    paths: set[str] = set()
    buckets = [
        _run_git("diff", "--name-only"),
        _run_git("diff", "--cached", "--name-only"),
        _run_git("ls-files", "--others", "--exclude-standard"),
    ]
    for bucket in buckets:
        for line in bucket.splitlines():
            raw = line.strip()
            if raw:
                paths.add(raw)
    return sorted(paths)


def _changed_files_since_ref(since_ref: str) -> list[str]:
    bucket = _run_git("diff", "--name-only", f"{since_ref}..HEAD")
    paths = [line.strip() for line in bucket.splitlines() if line.strip()]
    return sorted(dict.fromkeys(paths))


def _classify(path: str) -> str:
    p = path.replace("\\", "/")
    if "/cockpit/" in p:
        return "operator_surface"
    if "/backend/app/models/" in p or "/alembic/" in p or "analysis_report_schema" in p:
        return "data_contracts_and_schema"
    if any(
        token in p
        for token in [
            "full_history_ticker_sync.py",
            "asx_enrichment_sweep_action.py",
            "daily_asx_",
            "daily_marketindex_action.py",
            "resume_pending_downloads.py",
            "update_ticker_financials.py",
            "/backend/app/providers/",
            "/backend/app/services/pipeline.py",
            "/backend/app/services/announcement_importance.py",
        ]
    ):
        return "ingestion_pipeline"
    if "resource_library_workflow.py" in p:
        return "knowledge_curation"
    if p.endswith("run.py") or "/config/" in p or "docker-compose" in p or p.endswith("Makefile"):
        return "runtime_orchestration"
    if "/scripts/test_" in p or "/fixtures/" in p or "validate_analysis_report.py" in p:
        return "quality_gates_and_tests"
    if p.endswith(".md") or "log_change_impact.py" in p:
        return "docs_and_governance"
    return "other"


def _significance_reasons(paths: list[str]) -> list[str]:
    reasons: list[str] = []
    joined = "\n".join(paths)
    if any("/backend/app/models/" in p or "/alembic/" in p for p in paths):
        reasons.append("database/models changed")
    if any("cockpit/core/actions.py" in p or "cockpit/ui/" in p for p in paths):
        reasons.append("operator action/control surface changed")
    if any("analysis_report_schema.py" in p or "validate_analysis_report.py" in p for p in paths):
        reasons.append("report contract or quality gate changed")
    if any(
        token in joined
        for token in [
            "full_history_ticker_sync.py",
            "asx_enrichment_sweep_action.py",
            "daily_asx_all_announcements_action.py",
            "daily_asx_marketwide_action.py",
            "daily_marketindex_action.py",
            "update_ticker_financials.py",
        ]
    ):
        reasons.append("primary ingestion workflow changed")
    if any(p.endswith("run.py") or p.endswith("Makefile") for p in paths):
        reasons.append("entrypoint/orchestration changed")
    return reasons


def _build_digest(paths: list[str], mode: str, since_ref: str | None) -> dict:
    categories: dict[str, int] = {}
    for path in paths:
        key = _classify(path)
        categories[key] = categories.get(key, 0) + 1

    reasons = _significance_reasons(paths)
    significant = bool(reasons) or len(categories) >= 3
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": now,
        "mode": mode,
        "since_ref": since_ref,
        "repo": str(REPO_ROOT),
        "branch": _run_git("rev-parse", "--abbrev-ref", "HEAD") or None,
        "commit": _run_git("rev-parse", "HEAD") or None,
        "changed_files_count": len(paths),
        "changed_files": paths,
        "capability_impact": categories,
        "significant_change": significant,
        "significance_reasons": reasons,
    }
    return payload


def _summary_line(digest: dict) -> str:
    caps = digest.get("capability_impact", {})
    top = sorted(caps.items(), key=lambda kv: kv[1], reverse=True)
    top_txt = ", ".join(f"{k}:{v}" for k, v in top[:4]) if top else "none"
    return f"changes={digest['changed_files_count']} significant={digest['significant_change']} impact={top_txt}"


def _digest_markdown(digest: dict) -> str:
    lines = [
        "# Agent Context Digest",
        "",
        f"- Generated: {digest.get('generated_at')}",
        f"- Branch: {digest.get('branch')}",
        f"- Commit: {digest.get('commit')}",
        f"- Mode: {digest.get('mode')}",
        f"- Since ref: {digest.get('since_ref')}",
        f"- Changed files: {digest.get('changed_files_count')}",
        f"- Significant change: {digest.get('significant_change')}",
    ]
    reasons = digest.get("significance_reasons", [])
    if reasons:
        lines.append("- Significance reasons:")
        lines.extend([f"  - {item}" for item in reasons])
    lines.append("- Capability impact:")
    for key, value in sorted(digest.get("capability_impact", {}).items()):
        lines.append(f"  - {key}: {value}")
    lines.append("")
    lines.append("## High-level Context")
    lines.append("TENN is a local-first ASX ingestion, processing, and operator workflow system.")
    lines.append("Primary flow: discover -> insert -> download -> process -> classify -> report.")
    lines.append("Resource knowledge curation is human-gated; report citation gating is scaffolded.")
    lines.append("")
    return "\n".join(lines)


def _context_block(digest: dict) -> str:
    reasons = digest.get("significance_reasons", [])
    reason_text = ", ".join(reasons) if reasons else "none"
    summary = _summary_line(digest)
    return (
        f"{BEGIN_MARKER}\n"
        "[project]\n"
        'name = "tenn"\n'
        'active_runtime = "financial-engine-v2"\n'
        'domain = "ASX ingestion, extraction, operator workflows, and curated context"\n'
        "\n"
        "[project.agent_context]\n"
        f'last_refresh = "{digest.get("generated_at")}"\n'
        f'last_commit = "{digest.get("commit")}"\n'
        f'last_branch = "{digest.get("branch")}"\n'
        "summary = '''TENN is a local-first ASX ingestion platform with API, Cockpit TUI, and script orchestration surfaces. "
        "Core flow is discover -> insert -> download -> process -> classify -> report. "
        "Resource-library knowledge ingestion is human-gated and heuristic-first by default. "
        "Report schema validation and citation/evidence gating exist as scaffolded quality controls.'''"
        "\n"
        "\n"
        "[project.change_watch]\n"
        "enabled = true\n"
        f'last_digest = "{summary}"\n'
        f'last_significance_reasons = "{reason_text}"\n'
        "notify_on_significant_change = true\n"
        "significant_change_definition = '''Treat changes as significant if they alter ingestion behavior, "
        "data/report contracts, operator controls, runtime defaults, or quality gates.'''"
        "\n"
        f"{END_MARKER}\n"
    )


def _update_config_file(config_path: Path, block: str) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        text = config_path.read_text(encoding="utf-8")
    else:
        text = ""
    if BEGIN_MARKER in text and END_MARKER in text:
        start = text.index(BEGIN_MARKER)
        end = text.index(END_MARKER) + len(END_MARKER)
        new_text = text[:start].rstrip() + "\n\n" + block + "\n" + text[end:].lstrip()
    else:
        suffix = "\n\n" if text and not text.endswith("\n") else ""
        new_text = text + suffix + block
    config_path.write_text(new_text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh Codex project context and detect significant changes.")
    parser.add_argument("--since-ref", default="", help="Compare changes from <ref>..HEAD (e.g. origin/main).")
    parser.add_argument(
        "--mode",
        choices=["workspace", "since-ref"],
        default="workspace",
        help="workspace = uncommitted+untracked; since-ref = git diff from ref..HEAD.",
    )
    parser.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH), help="Codex config.toml path.")
    parser.add_argument("--digest-path", default=str(DEFAULT_DIGEST_PATH), help="Markdown digest output path.")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE_PATH), help="JSON state snapshot output path.")
    parser.add_argument("--write-config", action="store_true", help="Write/update context block in config.toml.")
    parser.add_argument("--check-significant", action="store_true", help="Exit non-zero if significant changes exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = args.mode
    since_ref = args.since_ref.strip() or None
    if mode == "since-ref":
        if not since_ref:
            raise SystemExit("--since-ref is required when --mode=since-ref")
        changed = _changed_files_since_ref(since_ref)
    else:
        changed = _changed_files_workspace()
        since_ref = None

    digest = _build_digest(paths=changed, mode=mode, since_ref=since_ref)

    digest_path = Path(args.digest_path)
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(_digest_markdown(digest), encoding="utf-8")

    state_path = Path(args.state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(digest, indent=2), encoding="utf-8")

    if args.write_config:
        _update_config_file(Path(args.config_path), _context_block(digest))
        print(f"Updated config context block: {args.config_path}")

    print(f"Wrote digest: {digest_path}")
    print(f"Wrote snapshot: {state_path}")
    print(_summary_line(digest))

    if args.check_significant and digest.get("significant_change"):
        print("Significant changes detected. Refresh config context and review impact log.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
