#!/usr/bin/env python3
"""Build a curated architecture-only graph scope for Tenn.

The full-repo graph mixes runtime architecture with tests, plans, screenshots, reports,
and generated artifacts. This script materializes a smaller corpus containing only the
contract docs, runtime docs, and the code entrypoints that define Tenn's core topology.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / ".tmp" / "architecture-graph-scope"

CURATED_PATHS = [
    "docs/architecture",
    "docs/entrypoints.md",
    "docs/tenn-system-map.html",
    "financial-engine_v2/backend/app/main.py",
    "financial-engine_v2/backend/app/api",
    "financial-engine_v2/backend/app/routes/cockpit_api.py",
    "financial-engine_v2/backend/app/services/router.py",
    "financial-engine_v2/backend/app/services/llm.py",
    "financial-engine_v2/backend/app/services/rag.py",
    "financial-engine_v2/backend/app/services/pipeline.py",
    "financial-engine_v2/backend/app/services/multipass_extraction.py",
    "financial-engine_v2/backend/app/celery_app.py",
    "financial-engine_v2/backend/app/worker_tasks.py",
    "financial-engine_v2/backend/app/models",
    "financial-engine_v2/cockpit/integrations/backend_api.py",
    "cockpit-ui/lib/api-client.ts",
    "scripts/run_llama_server.sh",
]

EXCLUDED_CLASSES = [
    "tests and test fixtures",
    "reports and generated graph artifacts",
    "screenshots, videos, and image evidence",
    "plans, brainstorms, and sprint notes",
    "playwright reports and temporary outputs",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Directory to write the curated scope into (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--run-graphify",
        action="store_true",
        help="Run `graphify update <scope>` after materializing the scope",
    )
    parser.add_argument(
        "graphify_args",
        nargs="*",
        help="Extra args passed through to graphify when --run-graphify is used",
    )
    return parser.parse_args()


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def copy_path(src: Path, dest_root: Path) -> None:
    dest = dest_root / src.relative_to(REPO_ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(
            src,
            dest,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
        )
    else:
        shutil.copy2(src, dest)


def write_manifest(output_dir: Path, copied_paths: list[Path]) -> None:
    manifest = output_dir / "ARCHITECTURE_SCOPE.md"
    lines = [
        "# Tenn Architecture Graph Scope",
        "",
        "This folder is a curated architecture-only corpus for graphify.",
        "",
        "Included paths:",
        *[f"- `{path.relative_to(REPO_ROOT)}`" for path in copied_paths],
        "",
        "Excluded classes of files:",
        *[f"- {entry}" for entry in EXCLUDED_CLASSES],
        "",
        "Use this scope when you want the graph to represent Tenn's runtime architecture",
        "instead of the entire repo's implementation, governance, testing, and artifact surface.",
    ]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def materialize_scope(output_dir: Path) -> list[Path]:
    reset_dir(output_dir)
    copied_paths: list[Path] = []
    for rel_path in CURATED_PATHS:
        src = REPO_ROOT / rel_path
        if not src.exists():
            raise FileNotFoundError(f"Curated architecture path missing: {src}")
        copy_path(src, output_dir)
        copied_paths.append(src)
    write_manifest(output_dir, copied_paths)
    return copied_paths


def count_files(output_dir: Path) -> int:
    return sum(1 for path in output_dir.rglob("*") if path.is_file())


def run_graphify(output_dir: Path, extra_args: list[str]) -> int:
    cmd = ["graphify", "update", str(output_dir), *extra_args]
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output).resolve()
    copied_paths = materialize_scope(output_dir)
    file_count = count_files(output_dir)

    print(f"Architecture scope written to {output_dir}")
    print(f"Curated inputs: {len(copied_paths)} root paths")
    print(f"Materialized files: {file_count}")

    if args.run_graphify:
        print(
            f"Running: graphify update {output_dir} {' '.join(args.graphify_args)}".rstrip()
        )
        return run_graphify(output_dir, args.graphify_args)

    print(f"Next: graphify update {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
