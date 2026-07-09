#!/usr/bin/env python3
"""Read-only GitHub dedupe gate for Tenn automation candidates."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any, Callable, Sequence


DEFAULT_REPO = "0rl4nd0l/tenn"
DEFAULT_LIMIT = 50
HIGH_CONFIDENCE_SCORE = 85
REVIEW_SCORE = 45
COMMAND_TIMEOUT_SECONDS = 30
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.:-]{1,}")
STOP_TOKENS = {
    "and",
    "for",
    "from",
    "into",
    "that",
    "the",
    "this",
    "with",
}
READ_ONLY_COMMANDS = {
    ("gh", "issue", "list"),
    ("gh", "pr", "list"),
}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CommandTrace:
    kind: str
    command: list[str]
    returncode: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Match:
    kind: str
    number: int | None
    title: str
    state: str
    url: str | None
    score: int
    confidence: str
    reasons: list[str]
    labels: list[str]
    head_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DedupeResult:
    status: str
    repo: str
    candidate: dict[str, Any]
    best_match: Match | None
    matches: list[Match]
    commands: list[CommandTrace]
    errors: list[str]
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "repo": self.repo,
            "candidate": self.candidate,
            "best_match": self.best_match.to_dict() if self.best_match else None,
            "matches": [match.to_dict() for match in self.matches],
            "commands": [command.to_dict() for command in self.commands],
            "errors": self.errors,
            "read_only": self.read_only,
        }


Runner = Callable[[list[str]], CommandResult]


def run_command(command: list[str]) -> CommandResult:
    if not is_read_only_gh_command(command):
        return CommandResult(2, "", f"blocked non-read-only command: {' '.join(command)}")
    try:
        proc = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        return CommandResult(124, stdout, stderr or f"command timed out after {COMMAND_TIMEOUT_SECONDS}s")
    return CommandResult(proc.returncode, proc.stdout, proc.stderr)


def is_read_only_gh_command(command: Sequence[str]) -> bool:
    return len(command) >= 3 and tuple(command[:3]) in READ_ONLY_COMMANDS


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(tokenize(value))


def tokenize(value: object) -> list[str]:
    if not isinstance(value, str):
        return []
    tokens = TOKEN_RE.findall(value.lower())
    return [token for token in tokens if token not in STOP_TOKENS and len(token) > 2]


def _clean_optional(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _candidate_payload(
    *,
    title: str,
    root_cause: str,
    fingerprint: str | None,
    related_issue: str | None,
    related_pr: str | None,
    url: str | None,
    labels: Sequence[str],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": title,
        "root_cause": root_cause,
        "labels": list(labels),
    }
    optional = {
        "fingerprint": fingerprint,
        "related_issue": related_issue,
        "related_pr": related_pr,
        "url": url,
    }
    payload.update({key: value for key, value in optional.items() if value})
    return payload


def build_search_query(
    *,
    title: str,
    root_cause: str,
    fingerprint: str | None = None,
    labels: Sequence[str] = (),
) -> str:
    del labels
    query = (fingerprint or title or root_cause or "automation").strip()
    return query[:512] or "automation"


def issue_list_command(repo: str, query: str, limit: int) -> list[str]:
    return [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        str(limit),
        "--search",
        query,
        "--json",
        "number,title,state,labels,url,updatedAt",
    ]


def pr_list_command(repo: str, query: str, limit: int) -> list[str]:
    return [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        str(limit),
        "--search",
        query,
        "--json",
        "number,title,state,isDraft,headRefName,baseRefName,labels,url,updatedAt",
    ]


def _read_json_list(command: list[str], kind: str, runner: Runner) -> tuple[list[dict[str, Any]], CommandTrace, str | None]:
    result = runner(command)
    trace = CommandTrace(kind=kind, command=command, returncode=result.returncode)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "command failed").strip()
        return [], trace, f"{kind} read failed: {message}"
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        return [], trace, f"{kind} returned invalid JSON: {exc}"
    if not isinstance(payload, list):
        return [], trace, f"{kind} returned non-list JSON"
    records = [item for item in payload if isinstance(item, dict)]
    return records, trace, None


def _number_text(value: object) -> str | None:
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip().lstrip("#").isdigit():
        return value.strip().lstrip("#")
    return None


def _record_labels(record: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for label in record.get("labels", []):
        if isinstance(label, dict):
            name = label.get("name")
        else:
            name = label
        if isinstance(name, str) and name:
            labels.append(name)
    return sorted(set(labels))


def _record_haystack(record: dict[str, Any]) -> str:
    values = [
        record.get("title"),
        record.get("url"),
        record.get("headRefName"),
        record.get("baseRefName"),
        " ".join(_record_labels(record)),
    ]
    return " ".join(str(value) for value in values if value)


def score_record(
    record: dict[str, Any],
    *,
    kind: str,
    title: str,
    root_cause: str,
    fingerprint: str | None = None,
    related_issue: str | None = None,
    related_pr: str | None = None,
    url: str | None = None,
) -> tuple[int, list[str]]:
    reasons: list[str] = []
    number = _number_text(record.get("number"))
    record_url = _clean_optional(record.get("url"))
    record_title = str(record.get("title") or "")
    haystack = _record_haystack(record)
    normalized_haystack = normalize_text(haystack)

    if kind == "issue" and related_issue and number == _number_text(related_issue):
        return 100, ["related_issue_exact"]
    if kind == "pr" and related_pr and number == _number_text(related_pr):
        return 100, ["related_pr_exact"]
    if url and record_url and url.rstrip("/") == record_url.rstrip("/"):
        return 100, ["url_exact"]
    if fingerprint and fingerprint.lower() in haystack.lower():
        return 96, ["fingerprint_exact"]
    if normalize_text(title) and normalize_text(title) == normalize_text(record_title):
        return 94, ["title_exact"]
    root_cause_tokens = tokenize(root_cause)
    if len(root_cause_tokens) >= 3 and normalize_text(root_cause) in normalized_haystack:
        return 88, ["root_cause_exact"]

    candidate_tokens = set(tokenize(f"{title} {root_cause}"))
    record_tokens = set(tokenize(haystack))
    if not candidate_tokens or not record_tokens:
        return 0, []
    overlap = candidate_tokens & record_tokens
    if not overlap:
        return 0, []
    overlap_ratio = len(overlap) / max(1, min(len(candidate_tokens), len(record_tokens)))
    if overlap_ratio >= 0.6:
        reasons.append("token_overlap_high")
        return 70, reasons
    if overlap_ratio >= 0.35:
        reasons.append("token_overlap_medium")
        return 50, reasons
    reasons.append("token_overlap_low")
    return 25, reasons


def build_match(
    kind: str,
    record: dict[str, Any],
    *,
    title: str,
    root_cause: str,
    fingerprint: str | None = None,
    related_issue: str | None = None,
    related_pr: str | None = None,
    url: str | None = None,
) -> Match | None:
    score, reasons = score_record(
        record,
        kind=kind,
        title=title,
        root_cause=root_cause,
        fingerprint=fingerprint,
        related_issue=related_issue,
        related_pr=related_pr,
        url=url,
    )
    if score <= 0:
        return None
    confidence = "high" if score >= HIGH_CONFIDENCE_SCORE else "medium" if score >= REVIEW_SCORE else "low"
    return Match(
        kind=kind,
        number=record.get("number") if isinstance(record.get("number"), int) else None,
        title=str(record.get("title") or ""),
        state=str(record.get("state") or "unknown"),
        url=record.get("url") if isinstance(record.get("url"), str) else None,
        score=score,
        confidence=confidence,
        reasons=reasons,
        labels=_record_labels(record),
        head_ref=record.get("headRefName") if isinstance(record.get("headRefName"), str) else None,
    )


def classify_matches(matches: Sequence[Match], errors: Sequence[str]) -> tuple[str, Match | None]:
    if errors:
        return "data_missing", None
    ranked = sorted(matches, key=lambda match: (match.score, 1 if match.kind == "pr" else 0), reverse=True)
    if not ranked:
        return "new", None
    best = ranked[0]
    if best.score >= HIGH_CONFIDENCE_SCORE:
        return f"duplicate_{best.kind}", best
    if best.score >= REVIEW_SCORE:
        return "needs_review", best
    return "new", None


def check_candidate(
    *,
    repo: str,
    title: str,
    root_cause: str,
    fingerprint: str | None = None,
    related_issue: str | None = None,
    related_pr: str | None = None,
    url: str | None = None,
    labels: Sequence[str] = (),
    limit: int = DEFAULT_LIMIT,
    runner: Runner = run_command,
) -> DedupeResult:
    query = build_search_query(title=title, root_cause=root_cause, fingerprint=fingerprint, labels=labels)
    issue_records, issue_trace, issue_error = _read_json_list(issue_list_command(repo, query, limit), "issues", runner)
    pr_records, pr_trace, pr_error = _read_json_list(pr_list_command(repo, query, limit), "prs", runner)
    errors = [error for error in (issue_error, pr_error) if error]

    matches: list[Match] = []
    for kind, records in (("issue", issue_records), ("pr", pr_records)):
        for record in records:
            match = build_match(
                kind,
                record,
                title=title,
                root_cause=root_cause,
                fingerprint=fingerprint,
                related_issue=related_issue,
                related_pr=related_pr,
                url=url,
            )
            if match:
                matches.append(match)
    matches.sort(key=lambda match: (match.score, 1 if match.kind == "pr" else 0), reverse=True)
    status, best_match = classify_matches(matches, errors)
    return DedupeResult(
        status=status,
        repo=repo,
        candidate=_candidate_payload(
            title=title,
            root_cause=root_cause,
            fingerprint=fingerprint,
            related_issue=related_issue,
            related_pr=related_pr,
            url=url,
            labels=labels,
        ),
        best_match=best_match,
        matches=matches,
        commands=[issue_trace, pr_trace],
        errors=errors,
    )


def format_summary(result: DedupeResult) -> str:
    lines = [f"status: {result.status}", f"repo: {result.repo}"]
    if result.best_match:
        match = result.best_match
        number = f"#{match.number}" if match.number is not None else "unknown"
        lines.append(f"best_match: {match.kind} {number} {match.title} ({match.confidence}, score={match.score})")
        if match.url:
            lines.append(f"url: {match.url}")
    if result.errors:
        lines.append("errors:")
        lines.extend(f"- {error}" for error in result.errors)
    lines.append("read_only: true")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="check one candidate against existing GitHub issues and PRs")
    check.add_argument("--repo", default=DEFAULT_REPO)
    check.add_argument("--title", required=True)
    check.add_argument("--root-cause", required=True)
    check.add_argument("--fingerprint")
    check.add_argument("--related-issue")
    check.add_argument("--related-pr")
    check.add_argument("--url")
    check.add_argument("--label", action="append", default=[])
    check.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    check.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "check":
        result = check_candidate(
            repo=args.repo,
            title=args.title,
            root_cause=args.root_cause,
            fingerprint=args.fingerprint,
            related_issue=args.related_issue,
            related_pr=args.related_pr,
            url=args.url,
            labels=args.label,
            limit=args.limit,
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            print(format_summary(result))
        return 1 if result.status == "data_missing" else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
