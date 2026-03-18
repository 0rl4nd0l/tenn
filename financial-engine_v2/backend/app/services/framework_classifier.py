from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np

from app.core.config import settings
from app.services.llm import embed_texts


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = REPO_ROOT.parent
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _default_embedding_fn(texts: list[str], *, ollama_url: str, model: str) -> list[list[float]]:
    return embed_texts(
        texts,
        metadata={
            "task_type": "embedding",
            "component": "framework_classifier",
            "operation": "framework_classification",
        },
    )


def _resolve_candidate_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()

    cwd_candidate = (Path.cwd() / expanded).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (REPO_ROOT / expanded).resolve()


def resolve_frameworks_path(frameworks_path: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if frameworks_path is not None:
        candidates.append(Path(frameworks_path))
    else:
        candidates.extend(
            [
                WORKSPACE_ROOT / "reports" / "investment_preprocess" / "framework_records" / "frameworks.jsonl",
                REPO_ROOT / "reports" / "investment_preprocess" / "framework_records" / "frameworks.jsonl",
                WORKSPACE_ROOT / "framework_records" / "frameworks.jsonl",
                REPO_ROOT / "framework_records" / "frameworks.jsonl",
            ]
        )

    checked: list[Path] = []
    seen = set()
    for candidate in candidates:
        resolved = _resolve_candidate_path(candidate)
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)
        checked.append(resolved)
        if resolved.exists():
            return resolved

    checked_text = "\n".join(f"- {candidate}" for candidate in checked) or "- <none>"
    raise FileNotFoundError(f"framework records file not found. Checked:\n{checked_text}")


def load_framework_records(frameworks_path: str | Path | None = None) -> list[dict[str, Any]]:
    path = resolve_frameworks_path(frameworks_path)
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, start=1):
            text = raw_line.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"framework record at line {lineno} is not a JSON object")
            records.append(payload)
    return records


def _tokenize(text: Any) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or ""))]


def _normalize_family(value: Any) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").lower())).strip("_")


def _humanize_family(value: str) -> str:
    return str(value or "").replace("_", " ").strip()


def _framework_text(record: dict[str, Any]) -> str:
    family = _humanize_family(_normalize_family(record.get("framework_family")))
    title = str(record.get("title") or "").strip()
    principles = " ".join(str(item).strip() for item in (record.get("principles") or []) if str(item).strip())
    return " ".join(part for part in (family, title, principles) if part).strip()


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    left_vector = np.asarray(left, dtype=float)
    right_vector = np.asarray(right, dtype=float)
    if left_vector.shape != right_vector.shape:
        return 0.0
    denominator = float(np.linalg.norm(left_vector) * np.linalg.norm(right_vector))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left_vector, right_vector) / denominator)


def _token_overlap(query_tokens: set[str], candidate_tokens: set[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    intersection = len(query_tokens & candidate_tokens)
    if intersection <= 0:
        return 0.0
    return float(intersection) / float(max(1, len(query_tokens)))


class FrameworkClassifier:
    def __init__(
        self,
        *,
        frameworks_path: str | Path | None = None,
        embedding_fn: Callable[..., list[list[float]]] | None = None,
        ollama_url: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.frameworks_path = resolve_frameworks_path(frameworks_path)
        self.framework_records = load_framework_records(self.frameworks_path)
        self.embedding_fn = embedding_fn or _default_embedding_fn
        self.ollama_url = str(ollama_url or settings.ollama_url)
        self.embed_model = str(embed_model or settings.embed_model)
        self._record_vectors: list[list[float]] | None = None

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.embedding_fn(texts, ollama_url=self.ollama_url, model=self.embed_model)

    def _ensure_record_vectors(self) -> list[list[float]]:
        if self._record_vectors is None:
            texts = [_framework_text(record) for record in self.framework_records]
            self._record_vectors = self._embed_texts(texts)
        return self._record_vectors

    def classify(
        self,
        query: str,
        *,
        top_k: int = 3,
        min_score: float = 0.35,
    ) -> list[str]:
        normalized_query = str(query or "").strip()
        limit = max(1, int(top_k))
        if not normalized_query or not self.framework_records:
            return []

        query_embeddings = self._embed_texts([normalized_query])
        if not query_embeddings:
            return []
        query_embedding = query_embeddings[0]
        record_vectors = self._ensure_record_vectors()

        query_tokens = set(_tokenize(normalized_query))
        family_scores: dict[str, float] = {}

        for record, vector in zip(self.framework_records, record_vectors):
            family = _normalize_family(record.get("framework_family"))
            if not family:
                continue
            embed_score = _cosine_similarity(query_embedding, vector)
            lexical_score = _token_overlap(query_tokens, set(_tokenize(_framework_text(record))))
            score = (0.9 * embed_score) + (0.1 * lexical_score)
            previous = family_scores.get(family)
            if previous is None or score > previous:
                family_scores[family] = score

        ranked = sorted(family_scores.items(), key=lambda item: (-item[1], item[0]))
        selected = [family for family, score in ranked if score >= float(min_score)][:limit]
        if selected:
            return selected
        return [family for family, _ in ranked[:1]]
