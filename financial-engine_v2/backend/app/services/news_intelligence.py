import hashlib
import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.orm import Session

from app.core.config import PROJECT_ROOT, settings
from app.models.documents import Document
from app.models.news_intelligence import CanonicalStory, NewsArticle, NewsNarrative, SourceCheckpoint
from app.services.embeddings import ensure_collection, upsert_points
from app.services.ollama import ollama_embed
from app.services.text_extract import extract_text_from_pdf


logger = logging.getLogger(__name__)

SENTIMENT_METHOD_VERSION = "lexicon_v1"
NARRATIVE_MAX_DAYS = 90
DATA_MISSING = "DATA_MISSING"

POSITIVE_TOKENS = {
    "beat",
    "beats",
    "benefit",
    "benefits",
    "buyback",
    "contract",
    "contracts",
    "deliver",
    "delivered",
    "dividend",
    "dividends",
    "growth",
    "improve",
    "improved",
    "improving",
    "increase",
    "increased",
    "outperform",
    "outperformed",
    "profit",
    "record",
    "resilient",
    "strong",
    "upgrade",
    "upgraded",
    "upside",
}
NEGATIVE_TOKENS = {
    "cut",
    "cuts",
    "decline",
    "declined",
    "declines",
    "delay",
    "delays",
    "downgrade",
    "downgraded",
    "fall",
    "falls",
    "impairment",
    "lawsuit",
    "loss",
    "miss",
    "missed",
    "outage",
    "risk",
    "risks",
    "strike",
    "volatile",
    "warning",
    "weaker",
    "weakness",
}
NARRATIVE_STOPWORDS = {
    "a",
    "an",
    "and",
    "announces",
    "announcement",
    "asx",
    "for",
    "from",
    "group",
    "in",
    "limited",
    "of",
    "on",
    "the",
    "to",
    "update",
    "with",
}
TICKER_PATTERN = re.compile(r"\bASX[:\s]+([A-Z]{2,5})\b")


@dataclass
class _StoryState:
    canonical_story_id: str
    title: str
    normalized_title: str
    article_ids: list[str]
    first_published_at: datetime | None
    last_seen_at: datetime | None
    sentiment_scores: list[float]
    sentiment_confidences: list[float]
    text_candidates: list[str]
    title_candidates: list[str]


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _canonicalize_url(url: str | None) -> str:
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        scheme = (parts.scheme or "https").lower()
        netloc = parts.netloc.lower()
        path = re.sub(r"/{2,}", "/", parts.path or "")
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        query_items = parse_qsl(parts.query, keep_blank_values=True)
        query = urlencode(sorted(query_items))
        return urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return raw


def _stable_hash(*parts: str) -> str:
    payload = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_title(title: str | None) -> str:
    text = str(title or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str | None) -> list[str]:
    return re.findall(r"[a-zA-Z]{2,}", str(text or "").lower())


def _score_sentiment(text: str | None) -> tuple[float, str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return 0.0, "neutral", 0.0
    pos = sum(1 for token in tokens if token in POSITIVE_TOKENS)
    neg = sum(1 for token in tokens if token in NEGATIVE_TOKENS)
    total_hits = pos + neg
    if total_hits == 0:
        return 0.0, "neutral", 0.0

    score = (pos - neg) / float(total_hits)
    score = max(-1.0, min(1.0, score))
    if score >= 0.1:
        label = "positive"
    elif score <= -0.1:
        label = "negative"
    else:
        label = "neutral"

    confidence = min(1.0, total_hits / 8.0)
    return score, label, confidence


def _resolve_pdf_path(path_value: str | None) -> Path | None:
    raw = str(path_value or "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def _extract_raw_text_if_available(pdf_path: str | None, pdf_sha256: str | None) -> str | None:
    status = str(pdf_sha256 or "").strip().lower()
    if not pdf_path:
        return None
    if status.startswith("blocked_marketindex"):
        return None
    path = _resolve_pdf_path(pdf_path)
    if path is None or not path.exists():
        return None
    try:
        text = extract_text_from_pdf(str(path))
    except Exception:
        return None
    trimmed = str(text or "").strip()
    return trimmed or None


def _source_label(url: str | None) -> str:
    canonical = _canonicalize_url(url)
    host = (urlsplit(canonical).netloc or "").lower()
    if "asx.com.au" in host:
        return "asx"
    if "marketindex.com.au" in host:
        return "marketindex"
    if host:
        return host
    return "unknown"


def _map_tickers(document: Document) -> tuple[list[str], float]:
    ticker = str(document.ticker or "").strip().upper()
    if ticker:
        return [ticker], 1.0

    title = str(document.title or "")
    url = str(document.source_url or "")
    text = f"{title} {url}"
    matches = sorted({token.upper() for token in TICKER_PATTERN.findall(text)})
    if matches:
        return matches, 0.8
    return [], 0.0


def _headline_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    return SequenceMatcher(a=left, b=right).ratio()


def _story_sentiment(sentiment_scores: list[float], confidences: list[float]) -> tuple[float, str, float]:
    if not sentiment_scores:
        return 0.0, "neutral", 0.0
    avg = sum(sentiment_scores) / float(len(sentiment_scores))
    avg_conf = sum(confidences) / float(len(confidences)) if confidences else 0.0
    if avg >= 0.1:
        label = "positive"
    elif avg <= -0.1:
        label = "negative"
    else:
        label = "neutral"
    return avg, label, max(0.0, min(1.0, avg_conf))


def _window_to_timedelta(window: str) -> timedelta:
    text = str(window or "30d").strip().lower()
    match = re.fullmatch(r"(\d+)\s*([hdw])", text)
    if not match:
        return timedelta(days=30)
    value = int(match.group(1))
    unit = match.group(2)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)
    return timedelta(weeks=value)


def _snapshot_anchor(db: Session, ticker: str) -> datetime:
    rows = (
        db.query(NewsArticle)
        .filter(NewsArticle.primary_ticker == ticker.upper())
        .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.ingested_at.desc())
        .limit(1)
        .all()
    )
    if not rows:
        return _now_utc()
    row = rows[0]
    return _utc(row.published_at) or _utc(row.ingested_at) or _now_utc()


def _windowed_articles(db: Session, ticker: str, window: str, *, anchor: datetime | None = None) -> list[NewsArticle]:
    ticker_symbol = ticker.upper()
    anchor_ts = anchor or _snapshot_anchor(db, ticker_symbol)
    cutoff = anchor_ts - _window_to_timedelta(window)
    rows = (
        db.query(NewsArticle)
        .filter(NewsArticle.primary_ticker == ticker_symbol)
        .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.ingested_at.desc(), NewsArticle.article_id.asc())
        .all()
    )
    filtered: list[NewsArticle] = []
    for row in rows:
        ts = _utc(row.published_at) or _utc(row.ingested_at)
        if ts is None or ts >= cutoff:
            filtered.append(row)
    return filtered


def _refresh_story_assignments(db: Session, ticker: str) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    article_rows = (
        db.query(NewsArticle)
        .filter(NewsArticle.primary_ticker == ticker_symbol)
        .order_by(NewsArticle.published_at.asc().nullslast(), NewsArticle.ingested_at.asc(), NewsArticle.article_id.asc())
        .all()
    )

    db.query(CanonicalStory).filter(CanonicalStory.ticker == ticker_symbol).delete(synchronize_session=False)
    if not article_rows:
        db.commit()
        return {"story_count": 0, "duplicate_count": 0}

    exact_keys: dict[str, str] = {}
    stories: dict[str, _StoryState] = {}
    story_collisions: Counter[str] = Counter()

    for article in article_rows:
        normalized_title = _normalize_title(article.title)
        story_id: str | None = None

        for exact_key in (article.canonical_url, article.content_hash, article.headline_hash):
            key = str(exact_key or "").strip()
            if key and key in exact_keys:
                story_id = exact_keys[key]
                break

        if story_id is None:
            best_story_id = None
            best_similarity = 0.0
            for candidate_story in stories.values():
                similarity = _headline_similarity(normalized_title, candidate_story.normalized_title)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_story_id = candidate_story.canonical_story_id
            if best_story_id and best_similarity >= 0.84:
                story_id = best_story_id

        if story_id is None:
            base_story_id = _stable_hash(ticker_symbol, normalized_title)
            suffix = story_collisions[base_story_id]
            story_collisions[base_story_id] += 1
            story_id = base_story_id if suffix == 0 else _stable_hash(base_story_id, str(suffix))
            stories[story_id] = _StoryState(
                canonical_story_id=story_id,
                title=article.title,
                normalized_title=normalized_title,
                article_ids=[],
                first_published_at=_utc(article.published_at),
                last_seen_at=_utc(article.published_at),
                sentiment_scores=[],
                sentiment_confidences=[],
                text_candidates=[],
                title_candidates=[],
            )

        state = stories[story_id]
        state.article_ids.append(article.article_id)
        published_at = _utc(article.published_at)
        if state.first_published_at is None or (published_at and published_at < state.first_published_at):
            state.first_published_at = published_at
            state.title = article.title
            state.normalized_title = normalized_title
        if state.last_seen_at is None or (published_at and published_at > state.last_seen_at):
            state.last_seen_at = published_at
        if article.sentiment_score is not None:
            state.sentiment_scores.append(float(article.sentiment_score))
        if article.sentiment_confidence is not None:
            state.sentiment_confidences.append(float(article.sentiment_confidence))
        if article.raw_text:
            state.text_candidates.append(article.raw_text)
        if article.title:
            state.title_candidates.append(article.title)

        article.canonical_story_id = story_id
        for exact_key in (article.canonical_url, article.content_hash, article.headline_hash):
            key = str(exact_key or "").strip()
            if key:
                exact_keys[key] = story_id

    duplicate_total = 0
    for story_id in sorted(stories.keys()):
        state = stories[story_id]
        average_score, sentiment_label, sentiment_confidence = _story_sentiment(
            state.sentiment_scores, state.sentiment_confidences
        )
        related_articles = sorted(state.article_ids)
        duplicate_count = max(0, len(related_articles) - 1)
        duplicate_total += duplicate_count
        story_text = None
        if state.text_candidates:
            story_text = max(state.text_candidates, key=len)
        if story_text is None:
            story_text = " ".join(state.title_candidates[:3]) if state.title_candidates else None

        db.add(
            CanonicalStory(
                canonical_story_id=state.canonical_story_id,
                ticker=ticker_symbol,
                title=state.title,
                normalized_title=state.normalized_title,
                primary_article_id=related_articles[0],
                related_articles=related_articles,
                duplicate_count=duplicate_count,
                first_published_at=state.first_published_at,
                last_seen_at=state.last_seen_at,
                story_text=story_text,
                sentiment_score=average_score,
                sentiment_label=sentiment_label,
                sentiment_confidence=sentiment_confidence,
                sentiment_method_version=SENTIMENT_METHOD_VERSION,
            )
        )

    db.commit()
    return {"story_count": len(stories), "duplicate_count": duplicate_total}


def _narrative_label(titles: list[str]) -> str:
    tokens: list[str] = []
    for title in titles:
        for token in _tokenize(title):
            if token in NARRATIVE_STOPWORDS:
                continue
            tokens.append(token)
    if not tokens:
        return "market update"
    counts = Counter(tokens)
    top = [word for word, _ in counts.most_common(4)]
    return " ".join(top)


def _refresh_narratives(db: Session, ticker: str, *, anchor: datetime | None = None) -> int:
    ticker_symbol = ticker.upper()
    anchor_ts = anchor or _snapshot_anchor(db, ticker_symbol)
    cutoff = anchor_ts - timedelta(days=NARRATIVE_MAX_DAYS)

    story_rows = (
        db.query(CanonicalStory)
        .filter(CanonicalStory.ticker == ticker_symbol)
        .order_by(CanonicalStory.first_published_at.asc().nullslast(), CanonicalStory.canonical_story_id.asc())
        .all()
    )
    working = []
    for story in story_rows:
        ts = _utc(story.first_published_at) or _utc(story.last_seen_at)
        if ts is None or ts >= cutoff:
            working.append(story)

    db.query(NewsNarrative).filter(NewsNarrative.ticker == ticker_symbol).delete(synchronize_session=False)
    if not working:
        db.commit()
        return 0

    clusters: dict[str, dict[str, Any]] = {}
    for story in working:
        ts = _utc(story.first_published_at) or anchor_ts
        month_bucket = ts.strftime("%Y-%m")
        key_prefix = f"{ticker_symbol}|{month_bucket}"
        assigned_key = None
        best_similarity = 0.0
        for cluster_key, cluster in clusters.items():
            if cluster["key_prefix"] != key_prefix:
                continue
            similarity = _headline_similarity(story.normalized_title, cluster["normalized_label"])
            if similarity > best_similarity:
                best_similarity = similarity
                assigned_key = cluster_key
        if assigned_key is None or best_similarity < 0.6:
            signature = _stable_hash(story.normalized_title)[:16]
            assigned_key = f"{key_prefix}|{signature}"
            clusters[assigned_key] = {
                "key_prefix": key_prefix,
                "normalized_label": story.normalized_title,
                "titles": [],
                "story_ids": [],
                "start_date": ts,
                "last_seen": _utc(story.last_seen_at) or ts,
                "sentiment_scores": [],
            }

        cluster = clusters[assigned_key]
        cluster["titles"].append(story.title)
        cluster["story_ids"].append(story.canonical_story_id)
        if ts < cluster["start_date"]:
            cluster["start_date"] = ts
        last_seen_story = _utc(story.last_seen_at) or ts
        if last_seen_story > cluster["last_seen"]:
            cluster["last_seen"] = last_seen_story
        if story.sentiment_score is not None:
            cluster["sentiment_scores"].append(float(story.sentiment_score))

    for key in sorted(clusters.keys()):
        cluster = clusters[key]
        story_ids = sorted(set(cluster["story_ids"]))
        titles = cluster["titles"]
        avg_sentiment = (
            sum(cluster["sentiment_scores"]) / float(len(cluster["sentiment_scores"]))
            if cluster["sentiment_scores"]
            else 0.0
        )
        sentiment_profile = {
            "avg_score": round(avg_sentiment, 4),
            "positive_count": sum(1 for score in cluster["sentiment_scores"] if score > 0.1),
            "negative_count": sum(1 for score in cluster["sentiment_scores"] if score < -0.1),
            "neutral_count": sum(1 for score in cluster["sentiment_scores"] if -0.1 <= score <= 0.1),
        }
        confidence = min(1.0, 0.2 + 0.2 * len(story_ids) + 0.4 * abs(avg_sentiment))
        narrative_id = _stable_hash(ticker_symbol, key, "|".join(story_ids))
        db.add(
            NewsNarrative(
                narrative_id=narrative_id,
                ticker=ticker_symbol,
                label=_narrative_label(titles),
                story_ids=story_ids,
                start_date=cluster["start_date"],
                last_seen=cluster["last_seen"],
                story_count=len(story_ids),
                sentiment_profile=sentiment_profile,
                confidence=round(confidence, 4),
            )
        )
    db.commit()
    return len(clusters)


def _update_source_checkpoints(db: Session, ticker: str, run_mode: str) -> None:
    ticker_symbol = ticker.upper()
    rows = (
        db.query(NewsArticle)
        .filter(NewsArticle.primary_ticker == ticker_symbol)
        .order_by(NewsArticle.ingested_at.desc(), NewsArticle.article_id.asc())
        .all()
    )
    grouped: dict[str, list[NewsArticle]] = {}
    for row in rows:
        grouped.setdefault(row.source, []).append(row)

    for source, source_rows in grouped.items():
        latest = source_rows[0]
        checkpoint = db.query(SourceCheckpoint).filter(SourceCheckpoint.source == source).first()
        if not checkpoint:
            checkpoint = SourceCheckpoint(source=source)
            db.add(checkpoint)
        checkpoint.run_mode = run_mode
        checkpoint.last_cursor = f"{ticker_symbol}:{len(source_rows)}"
        checkpoint.last_ingested_at = _utc(latest.ingested_at)
        checkpoint.last_article_count = len(source_rows)
    db.commit()


def _refresh_embeddings_for_ticker(db: Session, ticker: str) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    if not settings.enable_embeddings:
        return {"status": "disabled", "attempted": 0, "stored": 0}
    if not settings.enable_qdrant:
        return {
            "status": DATA_MISSING,
            "attempted": 0,
            "stored": 0,
            "requirements": ["ENABLE_QDRANT=true and reachable Qdrant instance"],
        }

    article_rows = (
        db.query(NewsArticle)
        .filter(NewsArticle.primary_ticker == ticker_symbol)
        .order_by(NewsArticle.article_id.asc())
        .all()
    )
    story_rows = (
        db.query(CanonicalStory)
        .filter(CanonicalStory.ticker == ticker_symbol)
        .order_by(CanonicalStory.canonical_story_id.asc())
        .all()
    )
    jobs: list[tuple[str, Any, str, str, dict[str, Any]]] = []
    for row in article_rows:
        if row.title:
            jobs.append(
                (
                    "article_headline",
                    row,
                    row.article_id,
                    row.title[:2048],
                    {"ticker": ticker_symbol, "article_id": row.article_id, "record_type": "article_headline"},
                )
            )
        if row.raw_text:
            jobs.append(
                (
                    "article_text",
                    row,
                    row.article_id,
                    row.raw_text[:4096],
                    {"ticker": ticker_symbol, "article_id": row.article_id, "record_type": "article_text"},
                )
            )
    for row in story_rows:
        text = str(row.story_text or row.title or "").strip()
        if not text:
            continue
        jobs.append(
            (
                "story_text",
                row,
                row.canonical_story_id,
                text[:4096],
                {"ticker": ticker_symbol, "story_id": row.canonical_story_id, "record_type": "story_text"},
            )
        )
    if not jobs:
        return {"status": "ok", "attempted": 0, "stored": 0}

    inputs = [job[3] for job in jobs]
    try:
        vectors = ollama_embed(settings.ollama_url, settings.embed_model, inputs)
    except Exception as exc:
        return {
            "status": DATA_MISSING,
            "attempted": len(jobs),
            "stored": 0,
            "requirements": [f"Ollama embedding endpoint reachable at {settings.ollama_url}"],
            "error": str(exc),
        }
    if not vectors:
        return {"status": "ok", "attempted": len(jobs), "stored": 0}

    try:
        client = QdrantClient(url=settings.qdrant_url)
        ensure_collection(client, settings.qdrant_collection, len(vectors[0]))
        points = []
        for index, vector in enumerate(vectors):
            kind, row, row_id, _, payload = jobs[index]
            vector_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"news-intel:{kind}:{row_id}"))
            payload = dict(payload)
            payload["vector_id"] = vector_id
            points.append({"id": vector_id, "vector": vector, "payload": payload})
            if kind == "article_headline":
                row.headline_vector_id = vector_id
            elif kind == "article_text":
                row.text_vector_id = vector_id
            else:
                row.story_vector_id = vector_id
        upsert_points(client, settings.qdrant_collection, points)
        db.commit()
    except Exception as exc:
        db.rollback()
        return {
            "status": DATA_MISSING,
            "attempted": len(jobs),
            "stored": 0,
            "requirements": [f"Reachable Qdrant at {settings.qdrant_url}"],
            "error": str(exc),
        }

    return {"status": "ok", "attempted": len(jobs), "stored": len(jobs)}


def _observability_metrics(db: Session, ticker: str, embedding_summary: dict[str, Any]) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    rows = db.query(NewsArticle).filter(NewsArticle.primary_ticker == ticker_symbol).all()
    if not rows:
        return {
            "articles_per_source": {},
            "duplicates_detected": 0,
            "mapping_success_rate": 0.0,
            "embedding_success_rate": 0.0,
            "sentiment_coverage": 0.0,
            "narratives_per_ticker": 0,
            "stale_sources": [],
        }

    articles_per_source = Counter(row.source for row in rows)
    mapped = sum(1 for row in rows if row.mapping_confidence > 0 and row.tickers)
    sentiment_present = sum(1 for row in rows if row.sentiment_score is not None)
    duplicate_count = (
        db.query(CanonicalStory)
        .filter(CanonicalStory.ticker == ticker_symbol)
        .with_entities(CanonicalStory.duplicate_count)
        .all()
    )
    duplicate_total = sum(int(item[0] or 0) for item in duplicate_count)

    narratives_count = db.query(NewsNarrative).filter(NewsNarrative.ticker == ticker_symbol).count()
    latest_by_source: dict[str, datetime] = {}
    for row in rows:
        ts = _utc(row.published_at) or _utc(row.ingested_at)
        if ts is None:
            continue
        existing = latest_by_source.get(row.source)
        if existing is None or ts > existing:
            latest_by_source[row.source] = ts
    stale_sources = []
    threshold = _snapshot_anchor(db, ticker_symbol) - timedelta(days=14)
    for source, latest in latest_by_source.items():
        if latest < threshold:
            stale_sources.append(source)
    stale_sources.sort()

    attempted = int(embedding_summary.get("attempted", 0))
    stored = int(embedding_summary.get("stored", 0))
    return {
        "articles_per_source": dict(sorted(articles_per_source.items())),
        "duplicates_detected": duplicate_total,
        "mapping_success_rate": round(mapped / float(len(rows)), 4),
        "embedding_success_rate": round((stored / float(attempted)) if attempted else 0.0, 4),
        "sentiment_coverage": round(sentiment_present / float(len(rows)), 4),
        "narratives_per_ticker": narratives_count,
        "stale_sources": stale_sources,
    }


def build_news_intelligence_for_ticker(db: Session, ticker: str, *, run_mode: str = "incremental") -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    docs = (
        db.query(Document)
        .filter(Document.ticker == ticker_symbol)
        .order_by(Document.published_at.asc().nullslast(), Document.ingested_at.asc(), Document.document_id.asc())
        .all()
    )
    if not docs:
        return {
            "ticker": ticker_symbol,
            "articles_processed": 0,
            "story_count": 0,
            "narrative_count": 0,
            "embedding": {"status": "disabled", "attempted": 0, "stored": 0},
            "observability": {},
            "unresolved_mappings": 0,
        }

    unresolved_mappings = 0
    for doc in docs:
        canonical_url = _canonicalize_url(doc.source_url)
        published_at = _utc(doc.published_at)
        ingested_at = _utc(doc.ingested_at) or _now_utc()
        title = str(doc.title or "ASX Announcement").strip() or "ASX Announcement"
        normalized_title = _normalize_title(title)
        article_id = _stable_hash(
            ticker_symbol,
            canonical_url or title,
            (published_at.isoformat() if published_at else ""),
        )

        article = db.query(NewsArticle).filter(NewsArticle.article_id == article_id).first()
        if not article:
            article = NewsArticle(article_id=article_id)
            db.add(article)

        tickers, mapping_confidence = _map_tickers(doc)
        if not tickers:
            unresolved_mappings += 1
            logger.warning("news mapping unresolved ticker=%s document_id=%s", ticker_symbol, doc.document_id)

        raw_text = article.raw_text
        if not raw_text:
            raw_text = _extract_raw_text_if_available(doc.pdf_path, doc.pdf_sha256)
        basis_text = raw_text or title
        sentiment_score, sentiment_label, sentiment_confidence = _score_sentiment(basis_text)

        article.document_id = str(doc.document_id)
        article.primary_ticker = ticker_symbol
        article.tickers = tickers
        article.mapping_confidence = mapping_confidence
        article.title = title
        article.normalized_title = normalized_title
        article.source = _source_label(canonical_url)
        article.url = str(doc.source_url or "")
        article.canonical_url = canonical_url
        article.language = "en"
        article.published_at = published_at
        article.ingested_at = ingested_at
        article.raw_text = raw_text
        article.headline_hash = _stable_hash(normalized_title)
        article.content_hash = _stable_hash(raw_text) if raw_text else None
        article.sentiment_score = sentiment_score
        article.sentiment_label = sentiment_label
        article.sentiment_confidence = sentiment_confidence
        article.sentiment_method_version = SENTIMENT_METHOD_VERSION

    db.commit()

    story_summary = _refresh_story_assignments(db, ticker_symbol)
    anchor_ts = _snapshot_anchor(db, ticker_symbol)
    narrative_count = _refresh_narratives(db, ticker_symbol, anchor=anchor_ts)
    embedding_summary = _refresh_embeddings_for_ticker(db, ticker_symbol)
    _update_source_checkpoints(db, ticker_symbol, run_mode)
    observability = _observability_metrics(db, ticker_symbol, embedding_summary)

    return {
        "ticker": ticker_symbol,
        "articles_processed": len(docs),
        "story_count": int(story_summary.get("story_count", 0)),
        "duplicates_detected": int(story_summary.get("duplicate_count", 0)),
        "narrative_count": narrative_count,
        "embedding": embedding_summary,
        "observability": observability,
        "unresolved_mappings": unresolved_mappings,
    }


def get_company_news(db: Session, ticker: str, window: str = "30d", limit: int = 20) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    anchor_ts = _snapshot_anchor(db, ticker_symbol)
    rows = _windowed_articles(db, ticker_symbol, window, anchor=anchor_ts)[: max(1, int(limit))]
    return {
        "ticker": ticker_symbol,
        "window": window,
        "anchor_time": anchor_ts.isoformat(),
        "items": [
            {
                "id": row.article_id,
                "title": row.title,
                "source": row.source,
                "url": row.canonical_url,
                "published_at": row.published_at,
                "ingested_at": row.ingested_at,
                "language": row.language,
                "canonical_story_id": row.canonical_story_id,
                "tickers": row.tickers,
                "mapping_confidence": row.mapping_confidence,
                "sentiment_score": row.sentiment_score,
                "sentiment_label": row.sentiment_label,
                "sentiment_confidence": row.sentiment_confidence,
                "sentiment_method_version": row.sentiment_method_version,
            }
            for row in rows
        ],
    }


def get_company_sentiment(db: Session, ticker: str, window: str = "30d") -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    anchor_ts = _snapshot_anchor(db, ticker_symbol)
    rows = _windowed_articles(db, ticker_symbol, window, anchor=anchor_ts)

    def _aggregate(delta: timedelta) -> dict[str, Any]:
        cutoff = anchor_ts - delta
        scoped = [row for row in rows if (_utc(row.published_at) or _utc(row.ingested_at) or anchor_ts) >= cutoff]
        scores = [float(row.sentiment_score) for row in scoped if row.sentiment_score is not None]
        avg = sum(scores) / float(len(scores)) if scores else 0.0
        return {"count": len(scoped), "average_score": round(avg, 4)}

    metrics_24h = _aggregate(timedelta(hours=24))
    metrics_7d = _aggregate(timedelta(days=7))
    metrics_30d = _aggregate(timedelta(days=30))

    recent_cutoff = anchor_ts - timedelta(days=7)
    previous_cutoff = anchor_ts - timedelta(days=14)
    recent_scores = [
        float(row.sentiment_score)
        for row in rows
        if row.sentiment_score is not None and (_utc(row.published_at) or _utc(row.ingested_at) or anchor_ts) >= recent_cutoff
    ]
    previous_scores = [
        float(row.sentiment_score)
        for row in rows
        if row.sentiment_score is not None
        and previous_cutoff <= (_utc(row.published_at) or _utc(row.ingested_at) or anchor_ts) < recent_cutoff
    ]
    recent_avg = sum(recent_scores) / float(len(recent_scores)) if recent_scores else 0.0
    previous_avg = sum(previous_scores) / float(len(previous_scores)) if previous_scores else 0.0
    delta = recent_avg - previous_avg
    if delta > 0.05:
        trend = "improving"
    elif delta < -0.05:
        trend = "deteriorating"
    else:
        trend = "flat"

    return {
        "ticker": ticker_symbol,
        "window": window,
        "anchor_time": anchor_ts.isoformat(),
        "method_version": SENTIMENT_METHOD_VERSION,
        "sentiment_24h": metrics_24h,
        "sentiment_7d": metrics_7d,
        "sentiment_30d": metrics_30d,
        "trend_direction": trend,
        "trend_delta_7d_vs_prior_7d": round(delta, 4),
    }


def get_company_narratives(db: Session, ticker: str, window: str = "30d", limit: int = 8) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    anchor_ts = _snapshot_anchor(db, ticker_symbol)
    cutoff = anchor_ts - _window_to_timedelta(window)
    rows = (
        db.query(NewsNarrative)
        .filter(NewsNarrative.ticker == ticker_symbol)
        .order_by(NewsNarrative.story_count.desc(), NewsNarrative.last_seen.desc().nullslast(), NewsNarrative.narrative_id.asc())
        .all()
    )
    selected = []
    for row in rows:
        if row.last_seen and _utc(row.last_seen) and _utc(row.last_seen) < cutoff:
            continue
        selected.append(row)
        if len(selected) >= max(1, int(limit)):
            break

    return {
        "ticker": ticker_symbol,
        "window": window,
        "anchor_time": anchor_ts.isoformat(),
        "items": [
            {
                "narrative_id": row.narrative_id,
                "ticker": row.ticker,
                "label": row.label,
                "story_ids": row.story_ids,
                "start_date": row.start_date,
                "last_seen": row.last_seen,
                "story_count": row.story_count,
                "sentiment_profile": row.sentiment_profile,
                "confidence": row.confidence,
            }
            for row in selected
        ],
    }


def get_company_news_snapshot(db: Session, ticker: str) -> dict[str, Any]:
    ticker_symbol = ticker.upper()
    anchor_ts = _snapshot_anchor(db, ticker_symbol)
    news = get_company_news(db, ticker_symbol, window="30d", limit=12)
    sentiment = get_company_sentiment(db, ticker_symbol, window="30d")
    narratives = get_company_narratives(db, ticker_symbol, window="30d", limit=5)

    coverage_density = {
        "articles_24h": sentiment["sentiment_24h"]["count"],
        "articles_7d": sentiment["sentiment_7d"]["count"],
        "articles_30d": sentiment["sentiment_30d"]["count"],
        "daily_average_30d": round(sentiment["sentiment_30d"]["count"] / 30.0, 4),
    }

    notable_changes: list[str] = []
    if sentiment["trend_direction"] == "improving":
        notable_changes.append("7d sentiment is improving versus prior week")
    elif sentiment["trend_direction"] == "deteriorating":
        notable_changes.append("7d sentiment is deteriorating versus prior week")
    if sentiment["sentiment_24h"]["count"] > max(3, sentiment["sentiment_7d"]["count"] // 2):
        notable_changes.append("elevated 24h coverage density")
    if not notable_changes:
        notable_changes.append("no significant sentiment or coverage shift detected")

    dominant_narratives = narratives["items"]
    latest_headlines = news["items"]
    supporting_ids = sorted(
        {
            item["id"]
            for item in latest_headlines
            if isinstance(item, dict) and item.get("id")
        }
    )

    return {
        "ticker": ticker_symbol,
        "anchor_time": anchor_ts.isoformat(),
        "latest_headlines": latest_headlines,
        "dominant_narratives": dominant_narratives,
        "sentiment_summary": {
            "sentiment_24h": sentiment["sentiment_24h"],
            "sentiment_7d": sentiment["sentiment_7d"],
            "sentiment_30d": sentiment["sentiment_30d"],
            "method_version": sentiment["method_version"],
        },
        "sentiment_trend": {
            "direction": sentiment["trend_direction"],
            "delta_7d_vs_prior_7d": sentiment["trend_delta_7d_vs_prior_7d"],
        },
        "notable_recent_changes": notable_changes,
        "coverage_density": coverage_density,
        "supporting_article_ids": supporting_ids,
    }


def semantic_news_search(db: Session, query: str, filters: dict[str, Any] | None = None, top_k: int = 8) -> dict[str, Any]:
    filters = dict(filters or {})
    text = str(query or "").strip()
    if not text:
        return {"query": text, "hits": [], "count": 0}
    if not settings.enable_embeddings or not settings.enable_qdrant:
        return {
            "status": DATA_MISSING,
            "requirements": ["ENABLE_EMBEDDINGS=true", "ENABLE_QDRANT=true", "reachable Ollama and Qdrant"],
            "query": text,
            "hits": [],
            "count": 0,
        }

    try:
        query_vector = ollama_embed(settings.ollama_url, settings.embed_model, [text])[0]
    except Exception as exc:
        return {
            "status": DATA_MISSING,
            "requirements": [f"Ollama embedding endpoint reachable at {settings.ollama_url}"],
            "query": text,
            "hits": [],
            "count": 0,
            "error": str(exc),
        }

    filter_clauses = []
    ticker = str(filters.get("ticker") or "").strip().upper()
    if ticker:
        filter_clauses.append(
            qmodels.FieldCondition(key="ticker", match=qmodels.MatchValue(value=ticker))
        )
    record_type = str(filters.get("record_type") or "").strip().lower()
    if record_type:
        filter_clauses.append(
            qmodels.FieldCondition(key="record_type", match=qmodels.MatchValue(value=record_type))
        )
    query_filter = qmodels.Filter(must=filter_clauses) if filter_clauses else None

    try:
        client = QdrantClient(url=settings.qdrant_url)
        hits = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=max(1, int(top_k)),
            with_payload=True,
        )
    except Exception as exc:
        return {
            "status": DATA_MISSING,
            "requirements": [f"Reachable Qdrant at {settings.qdrant_url}"],
            "query": text,
            "hits": [],
            "count": 0,
            "error": str(exc),
        }

    article_ids = sorted(
        {
            str((hit.payload or {}).get("article_id"))
            for hit in hits
            if isinstance(hit.payload, dict) and hit.payload.get("article_id")
        }
    )
    story_ids = sorted(
        {
            str((hit.payload or {}).get("story_id"))
            for hit in hits
            if isinstance(hit.payload, dict) and hit.payload.get("story_id")
        }
    )
    article_lookup = {
        row.article_id: row
        for row in db.query(NewsArticle).filter(NewsArticle.article_id.in_(article_ids)).all()
    } if article_ids else {}
    story_lookup = {
        row.canonical_story_id: row
        for row in db.query(CanonicalStory).filter(CanonicalStory.canonical_story_id.in_(story_ids)).all()
    } if story_ids else {}

    mapped_hits = []
    for hit in hits:
        payload = dict(hit.payload or {})
        article = article_lookup.get(str(payload.get("article_id")))
        story = story_lookup.get(str(payload.get("story_id")))
        mapped_hits.append(
            {
                "score": float(hit.score),
                "record_type": payload.get("record_type"),
                "ticker": payload.get("ticker"),
                "article_id": payload.get("article_id"),
                "story_id": payload.get("story_id"),
                "title": article.title if article else (story.title if story else None),
                "url": article.canonical_url if article else None,
            }
        )
    mapped_hits.sort(key=lambda row: (-row["score"], str(row.get("article_id") or row.get("story_id") or "")))
    return {"query": text, "hits": mapped_hits, "count": len(mapped_hits)}
