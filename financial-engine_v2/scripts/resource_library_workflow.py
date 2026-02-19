#!/usr/bin/env python3
"""Resource library workflow for custom-GPT style local knowledge ingestion.

Flow:
1) Drop files into data/resource_library/inbox
2) Run ingest -> creates review candidates
3) Run review -> approve/reject/edit
4) Run build-context -> produce context pack for analysis prompts
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path("data/resource_library")
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass
class LibraryPaths:
    root: Path
    inbox: Path
    processed: Path
    candidates: Path
    approved: Path
    rejected: Path
    extracted: Path
    contexts: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_paths(root: Path) -> LibraryPaths:
    return LibraryPaths(
        root=root,
        inbox=root / "inbox",
        processed=root / "processed",
        candidates=root / "candidates",
        approved=root / "approved",
        rejected=root / "rejected",
        extracted=root / "extracted_text",
        contexts=root / "contexts",
    )


def init_folders(paths: LibraryPaths) -> None:
    for p in [
        paths.inbox,
        paths.processed,
        paths.candidates,
        paths.approved,
        paths.rejected,
        paths.extracted,
        paths.contexts,
    ]:
        p.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "PDF ingestion requires PyMuPDF (`pymupdf`). Install backend dependencies first."
            ) from exc
        doc = fitz.open(path)
        return "\n".join(page.get_text("text") for page in doc).strip()
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def heuristic_takeaways(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    key_points = [s[:240] for s in sentences if len(s) > 30][:5]
    if not key_points and cleaned:
        key_points = [cleaned[:240]]
    return {
        "summary": cleaned[:500],
        "key_takeaways": key_points,
        "tags": [],
        "confidence": 0.4,
        "mode": "heuristic",
    }


def llm_takeaways(ollama_url: str, model: str, text: str, max_chars: int) -> dict[str, Any]:
    try:
        import httpx
    except ModuleNotFoundError as exc:
        raise RuntimeError("LLM mode requires `httpx`. Install backend dependencies first.") from exc

    clipped = (text or "")[:max_chars]
    prompt = (
        "You are extracting reusable knowledge from user-provided documents. "
        "Return ONLY valid JSON with this schema: "
        '{"summary":"string","key_takeaways":["string"],"tags":["string"],"confidence":0..1}. '
        "Focus on decision-useful facts and claims. Document text:\n\n" + clipped
    )
    with httpx.Client(timeout=240.0) as client:
        response = client.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        generated = response.json().get("response", "")

    match = re.search(r"\{.*\}", generated, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output.")
    parsed = json.loads(match.group(0))
    return {
        "summary": str(parsed.get("summary") or "").strip(),
        "key_takeaways": [str(x).strip() for x in (parsed.get("key_takeaways") or []) if str(x).strip()],
        "tags": [str(x).strip() for x in (parsed.get("tags") or []) if str(x).strip()],
        "confidence": float(parsed.get("confidence") or 0.0),
        "mode": "llm",
    }


def cmd_init(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root))
    init_folders(paths)
    print(f"Initialized resource library folders at {paths.root}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root))
    init_folders(paths)

    files = [p for p in sorted(paths.inbox.iterdir()) if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        print("No supported files found in inbox.")
        return 0

    for src in files:
        resource_id = str(uuid.uuid4())
        text = read_text(src)
        extracted_path = paths.extracted / f"{resource_id}.txt"
        extracted_path.write_text(text, encoding="utf-8")

        try:
            if args.no_llm:
                takeaways = heuristic_takeaways(text)
            else:
                takeaways = llm_takeaways(args.ollama_url, args.model, text, args.max_chars)
        except Exception as exc:
            print(f"LLM generation failed for {src.name}: {exc}. Falling back to heuristic mode.")
            takeaways = heuristic_takeaways(text)

        payload = {
            "resource_id": resource_id,
            "source_file": src.name,
            "source_path": str(src),
            "status": "pending_review",
            "created_at": utc_now(),
            "summary": takeaways["summary"],
            "key_takeaways": takeaways["key_takeaways"],
            "tags": takeaways["tags"],
            "confidence": takeaways["confidence"],
            "generation_mode": takeaways["mode"],
            "extracted_text_path": str(extracted_path),
        }
        candidate_path = paths.candidates / f"{resource_id}.json"
        candidate_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        destination = paths.processed / src.name
        if destination.exists():
            destination = paths.processed / f"{resource_id}_{src.name}"
        shutil.move(str(src), str(destination))
        print(f"Created candidate: {candidate_path.name}")

    return 0


def _prompt(message: str) -> str:
    print(message, end="", flush=True)
    return sys.stdin.readline().strip()


def cmd_review(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root))
    init_folders(paths)
    candidates = sorted(paths.candidates.glob("*.json"))
    if args.limit > 0:
        candidates = candidates[: args.limit]
    if not candidates:
        print("No pending candidates.")
        return 0

    for candidate_file in candidates:
        payload = json.loads(candidate_file.read_text(encoding="utf-8"))
        print("\n" + "=" * 80)
        print(f"Resource: {payload['source_file']} ({payload['resource_id']})")
        print(f"Summary: {payload.get('summary', '')[:500]}")
        print("Takeaways:")
        for i, item in enumerate(payload.get("key_takeaways", []), 1):
            print(f"  {i}. {item}")

        action = _prompt("[a]pprove [r]eject [e]dit [s]kip [q]uit > ").lower()
        if action == "q":
            break
        if action == "s":
            continue
        if action == "e":
            new_summary = _prompt("New summary (blank keeps current): ")
            if new_summary:
                payload["summary"] = new_summary
            new_takeaways = _prompt("New takeaways separated by '||' (blank keeps current): ")
            if new_takeaways:
                payload["key_takeaways"] = [x.strip() for x in new_takeaways.split("||") if x.strip()]
            action = _prompt("Now [a]pprove or [r]eject? ").lower()

        payload["reviewed_at"] = utc_now()
        if action == "a":
            payload["status"] = "approved"
            out = paths.approved / candidate_file.name
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            candidate_file.unlink()
            print(f"Approved -> {out}")
        elif action == "r":
            payload["status"] = "rejected"
            out = paths.rejected / candidate_file.name
            out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            candidate_file.unlink()
            print(f"Rejected -> {out}")

    return 0


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9]{3,}", text.lower())}


def cmd_build_context(args: argparse.Namespace) -> int:
    paths = get_paths(Path(args.root))
    init_folders(paths)
    approved = sorted(paths.approved.glob("*.json"))
    if not approved:
        print("No approved resources found.")
        return 1

    q_tokens = _tokens(args.query)
    scored = []
    for item in approved:
        payload = json.loads(item.read_text(encoding="utf-8"))
        combined = " ".join([payload.get("summary", "")] + payload.get("key_takeaways", []))
        score = len(q_tokens.intersection(_tokens(combined)))
        scored.append((score, payload))

    scored.sort(key=lambda x: x[0], reverse=True)
    chosen = [p for score, p in scored[: args.top_k] if score > 0] or [p for _, p in scored[: args.top_k]]

    lines = [f"# Context Pack\n", f"Query: {args.query}\n", ""]
    for idx, payload in enumerate(chosen, 1):
        lines.append(f"## Source {idx}: {payload.get('source_file')}\n")
        lines.append(f"Summary: {payload.get('summary', '')}\n")
        lines.append("Key takeaways:")
        for point in payload.get("key_takeaways", []):
            lines.append(f"- {point}")
        lines.append("")

    output = "\n".join(lines).strip() + "\n"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = paths.contexts / f"context_{ts}.md"
    out_path.write_text(output, encoding="utf-8")
    print(output)
    print(f"Saved context pack: {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resource library workflow for analysis context.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="Library root path.")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Create library folders.")

    ingest = sub.add_parser("ingest", help="Ingest files from inbox into review candidates.")
    ingest.add_argument("--ollama-url", default="http://localhost:11434")
    ingest.add_argument("--model", default="llama3.1:8b")
    ingest.add_argument("--max-chars", type=int, default=16000)
    ingest_mode = ingest.add_mutually_exclusive_group()
    ingest_mode.add_argument(
        "--no-llm",
        dest="no_llm",
        action="store_true",
        help="Use heuristic summaries only (default).",
    )
    ingest_mode.add_argument(
        "--use-llm",
        dest="no_llm",
        action="store_false",
        help="Use Ollama-generated summaries/takeaways.",
    )
    ingest.set_defaults(no_llm=True)

    review = sub.add_parser("review", help="Approve/reject/edit pending candidates.")
    review.add_argument("--limit", type=int, default=0)

    context = sub.add_parser("build-context", help="Build a context pack from approved resources.")
    context.add_argument("--query", required=True)
    context.add_argument("--top-k", type=int, default=5)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    if args.command == "ingest":
        return cmd_ingest(args)
    if args.command == "review":
        return cmd_review(args)
    if args.command == "build-context":
        return cmd_build_context(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
