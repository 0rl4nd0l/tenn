#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_PATH = REPO_ROOT / "reports" / "traceability" / "protected_data_baseline.json"
DEFAULT_PROTECTED_ROOTS = [
    "financial-engine_v2/data/asx/docs",
    "financial-engine_v2/data/marketindex/pdfs",
    "reports/qual_context",
    "reports/review_packs",
]
HASH_CHUNK_BYTES = 64 * 1024
HashMode = Literal["metadata", "sample", "full"]


@dataclass(frozen=True)
class FileEntry:
    path: str
    size: int
    mtime_ns: int
    fingerprint: str | None


def _rel_to_repo(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT).as_posix())


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            candidate = Path(dirpath) / filename
            try:
                if candidate.is_file():
                    yield candidate
            except OSError:
                continue


def _sha256_bytes(parts: Iterable[bytes]) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part)
    return h.hexdigest()


def _fingerprint(path: Path, *, size: int, mode: HashMode) -> str | None:
    if mode == "metadata":
        return None

    if mode == "full":
        h = hashlib.sha256()
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()

    # sample mode: size + first and last 64KiB.
    first = b""
    last = b""
    with path.open("rb") as f:
        first = f.read(HASH_CHUNK_BYTES)
        if size > HASH_CHUNK_BYTES:
            tail_len = min(HASH_CHUNK_BYTES, size)
            f.seek(size - tail_len)
            last = f.read(tail_len)
    size_token = str(size).encode("utf-8")
    return _sha256_bytes([size_token, b"\n", first, b"\n", last])


def _build_snapshot(roots: List[Path], *, hash_mode: HashMode) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    snapshot: dict = {
        "generated_at": generated_at,
        "repo_root": str(REPO_ROOT),
        "hash_mode": hash_mode,
        "roots": [_rel_to_repo(root) for root in roots],
        "entries": {},
        "summary": {
            "file_count": 0,
            "total_bytes": 0,
        },
    }

    total_files = 0
    total_bytes = 0

    for root in roots:
        root_key = _rel_to_repo(root)
        files_out: List[dict] = []
        root_files = 0
        root_bytes = 0

        for fpath in _iter_files(root):
            try:
                st = fpath.stat()
            except OSError:
                continue
            size = int(st.st_size)
            mtime_ns = int(st.st_mtime_ns)
            fp = _fingerprint(fpath, size=size, mode=hash_mode)
            entry = FileEntry(
                path=_rel_to_repo(fpath),
                size=size,
                mtime_ns=mtime_ns,
                fingerprint=fp,
            )
            files_out.append(
                {
                    "path": entry.path,
                    "size": entry.size,
                    "mtime_ns": entry.mtime_ns,
                    "fingerprint": entry.fingerprint,
                }
            )
            root_files += 1
            root_bytes += size

        snapshot["entries"][root_key] = {
            "file_count": root_files,
            "total_bytes": root_bytes,
            "files": files_out,
        }
        total_files += root_files
        total_bytes += root_bytes

    snapshot["summary"]["file_count"] = total_files
    snapshot["summary"]["total_bytes"] = total_bytes
    return snapshot


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_file_map(snapshot: dict) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for payload in snapshot.get("entries", {}).values():
        for row in payload.get("files", []):
            path = str(row.get("path", "")).strip()
            if not path:
                continue
            out[path] = row
    return out


def _compare(baseline: dict, current: dict, *, strict_new: bool) -> Tuple[int, list[str]]:
    base_mode = str(baseline.get("hash_mode", "metadata"))
    cur_mode = str(current.get("hash_mode", "metadata"))
    if base_mode != cur_mode:
        return 2, [f"hash_mode mismatch: baseline={base_mode} current={cur_mode}"]

    base = _to_file_map(baseline)
    cur = _to_file_map(current)
    base_paths = set(base.keys())
    cur_paths = set(cur.keys())

    missing = sorted(base_paths - cur_paths)
    new = sorted(cur_paths - base_paths)
    changed: list[str] = []

    for path in sorted(base_paths & cur_paths):
        brow = base[path]
        crow = cur[path]
        if int(brow.get("size", -1)) != int(crow.get("size", -1)):
            changed.append(path)
            continue
        # For non-metadata modes, fingerprint mismatch indicates content mutation.
        bfp = brow.get("fingerprint")
        cfp = crow.get("fingerprint")
        if base_mode != "metadata" and bfp != cfp:
            changed.append(path)

    messages: list[str] = []
    if missing:
        messages.append(f"missing files: {len(missing)}")
        for item in missing[:25]:
            messages.append(f"  - {item}")
        if len(missing) > 25:
            messages.append(f"  - ... {len(missing) - 25} more")
    if changed:
        messages.append(f"changed files: {len(changed)}")
        for item in changed[:25]:
            messages.append(f"  - {item}")
        if len(changed) > 25:
            messages.append(f"  - ... {len(changed) - 25} more")
    if new:
        severity = "new files (strict)" if strict_new else "new files (allowed)"
        messages.append(f"{severity}: {len(new)}")
        for item in new[:25]:
            messages.append(f"  - {item}")
        if len(new) > 25:
            messages.append(f"  - ... {len(new) - 25} more")

    failed = bool(missing or changed or (strict_new and new))
    if failed:
        return 3, messages
    if not messages:
        messages.append("no missing/changed files detected")
    return 0, messages


def _parse_roots(raw_roots: List[str]) -> List[Path]:
    out: list[Path] = []
    for raw in raw_roots:
        rel = raw.strip().strip("/")
        if not rel:
            continue
        out.append((REPO_ROOT / rel).resolve())
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Protect large context/system datasets with a non-destructive baseline + verify workflow. "
            "This tool never deletes or moves files."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Write a baseline snapshot.")
    snap.add_argument("--baseline", default=str(DEFAULT_BASELINE_PATH), help="Baseline output JSON path.")
    snap.add_argument(
        "--roots",
        nargs="+",
        default=DEFAULT_PROTECTED_ROOTS,
        help="Repo-relative directories to include in the baseline.",
    )
    snap.add_argument(
        "--hash-mode",
        choices=["metadata", "sample", "full"],
        default="sample",
        help="metadata=fastest, sample=first+last chunk hash, full=full-file SHA256.",
    )

    verify = sub.add_parser("verify", help="Verify current state against baseline.")
    verify.add_argument("--baseline", default=str(DEFAULT_BASELINE_PATH), help="Baseline input JSON path.")
    verify.add_argument(
        "--strict-new",
        action="store_true",
        help="Treat newly added files as failure (default only fails on missing/changed files).",
    )
    verify.add_argument(
        "--write-current",
        default="",
        help="Optional path to write current snapshot JSON used for verification.",
    )

    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "snapshot":
        roots = _parse_roots(args.roots)
        snapshot = _build_snapshot(roots, hash_mode=args.hash_mode)
        out_path = Path(args.baseline)
        _write_json(out_path, snapshot)
        print(f"baseline_written={out_path}")
        print(f"hash_mode={snapshot['hash_mode']}")
        print(f"file_count={snapshot['summary']['file_count']}")
        print(f"total_bytes={snapshot['summary']['total_bytes']}")
        return 0

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"baseline_not_found={baseline_path}")
        return 2

    baseline = _load_json(baseline_path)
    roots = _parse_roots(list(baseline.get("roots", [])))
    hash_mode = str(baseline.get("hash_mode", "metadata"))
    if hash_mode not in {"metadata", "sample", "full"}:
        print(f"unsupported_hash_mode_in_baseline={hash_mode}")
        return 2

    current = _build_snapshot(roots, hash_mode=hash_mode)  # type: ignore[arg-type]
    if args.write_current:
        _write_json(Path(args.write_current), current)
        print(f"current_snapshot_written={args.write_current}")

    code, messages = _compare(baseline, current, strict_new=bool(args.strict_new))
    print(f"verify_exit_code={code}")
    for line in messages:
        print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
