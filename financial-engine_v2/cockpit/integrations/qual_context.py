from __future__ import annotations

import importlib.util
import json
import math
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency guard
    yaml = None


DEFAULT_NEWS_WEIGHTING_CONFIG: dict[str, Any] = {
    "enable_signal_weighting": True,
    "recency_half_life_hours": 24.0,
    "recency_max_boost": 0.35,
    "ticker_match_boosts": {
        "exact": 0.24,
        "strong": 0.14,
        "weak": 0.06,
    },
    "au_domain_boost": 0.05,
    "au_domain_suffixes": [".com.au", ".au"],
    "title_keyword_boost": 0.05,
    "title_keywords": [
        "earnings",
        "guidance",
        "downgrade",
        "upgrade",
        "dividend",
        "profit",
        "rba",
        "asx",
    ],
    "ticker_identity_map_path": "config/ticker_identity_map.json",
    "ticker_identity": {
        "enable_identity_hardening": True,
        "canonical_name_required_for_acronym": True,
        "acronym_min_length": 4,
        "downgrade_ambiguous_acronym_boost": 0.02,
        "allow_headline_only_medium": True,
        "headline_only_body_chars": 120,
    },
}


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_datetime_utc(raw_value: Any) -> datetime | None:
    raw = str(raw_value or "").strip()
    if not raw:
        return None

    txt = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(txt)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                break
            except Exception:
                continue
        else:
            return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _contains_keyword_boundary(text: str, keyword: str) -> bool:
    token = str(keyword or "").strip()
    if not token:
        return False
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
    )


def _contains_phrase_boundary(text: str, phrase: str) -> bool:
    token = str(phrase or "").strip()
    if not token:
        return False
    escaped = re.escape(token).replace(r"\ ", r"\s+")
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])",
            str(text or ""),
            flags=re.IGNORECASE,
        )
    )


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def load_ticker_identity_map(path: str) -> dict[str, Any]:
    raw_path = str(path or "").strip()
    if not raw_path:
        return {}

    identity_path = Path(raw_path).expanduser()
    if not identity_path.is_absolute():
        identity_path = (Path.cwd() / identity_path).resolve()

    if not identity_path.exists() or not identity_path.is_file():
        return {}

    try:
        payload = json.loads(identity_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {}
    for raw_ticker, raw_entry in payload.items():
        ticker = str(raw_ticker or "").strip().upper()
        if not ticker:
            continue
        entry = raw_entry if isinstance(raw_entry, dict) else {}
        normalized[ticker] = {
            "canonical_names": _as_string_list(entry.get("canonical_names")),
            "aliases": _as_string_list(entry.get("aliases")),
        }
    return normalized


def evaluate_ticker_identity_strength(
    ticker: str,
    title: str,
    body: str,
    identity_map: dict,
    config: dict,
) -> str:
    symbol = str(ticker or "").strip().upper()
    if not symbol:
        return "none"

    cfg = config if isinstance(config, dict) else {}
    identity_data = identity_map if isinstance(identity_map, dict) else {}
    entry = identity_data.get(symbol) if isinstance(identity_data.get(symbol), dict) else {}

    title_txt = str(title or "")
    body_txt = str(body or "")
    payload = f"{title_txt}\n{body_txt[:3500]}"
    payload_lower = payload.lower()
    title_lower = title_txt.lower()
    body_lower = body_txt.lower()

    allow_headline_only_medium = bool(cfg.get("allow_headline_only_medium", False))
    headline_body_chars = int(max(1, int(cfg.get("headline_only_body_chars", 120) or 120)))
    body_is_short = len(body_txt.strip()) < headline_body_chars
    source_domain = str(cfg.get("_source_domain") or cfg.get("source_domain") or "").strip().lower()
    source_is_au = bool(cfg.get("_source_is_au", False) or cfg.get("source_is_au", False))
    feed_is_au = bool(cfg.get("_feed_is_au", False) or cfg.get("feed_is_au", False))
    if source_domain.startswith("www."):
        source_domain = source_domain[4:]
    if source_domain.endswith(".au"):
        source_is_au = True
    source_au_eligible = bool(source_is_au or feed_is_au)

    canonical_terms: list[str] = []
    canonical_terms.extend(_as_string_list(entry.get("canonical_names")))
    canonical_terms.extend(_as_string_list(entry.get("aliases")))
    for term in canonical_terms:
        term_lower = str(term or "").strip().lower()
        if not term_lower:
            continue
        in_title = _contains_phrase_boundary(title_txt, term_lower)
        in_body = _contains_phrase_boundary(body_txt, term_lower)
        if in_body:
            return "strong"
        if in_title:
            if allow_headline_only_medium and body_is_short and source_au_eligible:
                return "medium"
            return "strong"

    if re.search(rf"\bASX\s*[:\-]\s*{re.escape(symbol)}\b", payload, flags=re.IGNORECASE):
        return "medium"
    if re.search(rf"(?<![A-Za-z0-9]){re.escape(symbol)}\.AX(?![A-Za-z0-9])", payload, flags=re.IGNORECASE):
        return "medium"

    if bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(symbol)}(?![A-Za-z0-9])", payload, flags=re.IGNORECASE)):
        acronym_min_length = int(max(1, int(cfg.get("acronym_min_length", 4))))
        canonical_required = bool(cfg.get("canonical_name_required_for_acronym", True))
        if canonical_required and canonical_terms:
            # If we have known canonical names but only saw acronym form, treat as ambiguous.
            return "ambiguous"
        if len(symbol) < acronym_min_length:
            return "weak"
        if canonical_required:
            return "ambiguous"
        return "weak"

    return "none"


def compute_news_weighted_score(
    semantic_score: float,
    published_at: str,
    ticker_match_mode: str,
    title: str,
    source_domain: str,
    config: dict,
    ticker_identity_strength: str = "",
) -> float:
    base_score = _safe_float(semantic_score, 0.0)
    cfg = config if isinstance(config, dict) else {}
    if not bool(cfg.get("enable_signal_weighting", False)):
        return base_score

    final_score = float(base_score)

    half_life_hours = max(1.0, _safe_float(cfg.get("recency_half_life_hours"), 24.0))
    max_boost = max(0.0, _safe_float(cfg.get("recency_max_boost"), 0.0))
    now_cfg = cfg.get("now_utc")
    now_utc = _parse_datetime_utc(now_cfg) if now_cfg is not None else None
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)
    published_utc = _parse_datetime_utc(published_at)
    if published_utc is not None and max_boost > 0:
        age_seconds = max(0.0, (now_utc - published_utc).total_seconds())
        decay = math.exp(-math.log(2.0) * (age_seconds / (half_life_hours * 3600.0)))
        final_score += min(max_boost, max_boost * decay)

    ticker_mode = str(ticker_match_mode or "").strip().lower()
    raw_ticker_boosts = cfg.get("ticker_match_boosts")
    ticker_boosts = raw_ticker_boosts if isinstance(raw_ticker_boosts, dict) else {}
    exact_boost = max(0.0, _safe_float(ticker_boosts.get("exact"), 0.0))
    strong_boost = max(0.0, _safe_float(ticker_boosts.get("strong"), 0.0))
    weak_boost = max(0.0, _safe_float(ticker_boosts.get("weak"), 0.0))
    identity_cfg = cfg.get("ticker_identity") if isinstance(cfg.get("ticker_identity"), dict) else {}
    identity_hardening_enabled = bool(identity_cfg.get("enable_identity_hardening", False))
    ticker_boost = 0.0
    if identity_hardening_enabled:
        strength = str(ticker_identity_strength or "").strip().lower()
        ambiguous_boost = max(
            0.0,
            _safe_float(
                identity_cfg.get(
                    "downgrade_ambiguous_acronym_boost",
                    cfg.get("downgrade_ambiguous_acronym_boost", 0.02),
                ),
                0.02,
            ),
        )
        if strength == "strong":
            ticker_boost = exact_boost
        elif strength == "medium":
            ticker_boost = strong_boost
        elif strength == "weak":
            ticker_boost = weak_boost
        elif strength == "ambiguous":
            ticker_boost = ambiguous_boost
    else:
        if ticker_mode in {"exact", "rank_1", "1"}:
            ticker_boost = exact_boost
        elif ticker_mode in {"strong", "qualified", "rank_2", "2"}:
            ticker_boost = strong_boost
        elif ticker_mode in {"weak", "boundary", "rank_3", "3"}:
            ticker_boost = weak_boost
    final_score += ticker_boost

    domain = str(source_domain or "").strip().lower()
    if domain:
        if domain.startswith("www."):
            domain = domain[4:]
        suffixes_cfg = cfg.get("au_domain_suffixes")
        suffixes = suffixes_cfg if isinstance(suffixes_cfg, list) else [".com.au", ".au"]
        au_boost = max(0.0, _safe_float(cfg.get("au_domain_boost"), 0.0))
        if any(domain.endswith(str(sfx).strip().lower()) for sfx in suffixes):
            final_score += au_boost

    title_text = str(title or "")
    keyword_boost = max(0.0, _safe_float(cfg.get("title_keyword_boost"), 0.0))
    if keyword_boost > 0:
        keywords_cfg = cfg.get("title_keywords")
        keywords = keywords_cfg if isinstance(keywords_cfg, list) else []
        if any(_contains_keyword_boundary(title_text, str(keyword)) for keyword in keywords):
            final_score += keyword_boost

    return float(final_score)


class QualContextReader:
    """Thin wrapper around scripts/build_qualitative_context_db.py query_sqlite().

    Cockpit itself does not implement vector retrieval. This adapter lets Cockpit
    reuse the existing qualitative context SQLite store (and its embedding
    backend) when available.
    """

    CACHE_TTL_SECONDS = 30.0
    MAX_CACHE = 64

    def __init__(
        self,
        repo_root: Path,
        *,
        db_path: str,
        embed_backend: str = "sentence-transformers",
        embed_model: str = "bge-large-en-v1.5",
        corpus_filter: str = "company",
        exclude_corpus_filter: str = "",
        top_k: int = 8,
        max_text_chars: int = 1200,
        ollama_endpoint: str = "http://127.0.0.1:11434",
        hash_dim: int = 384,
        st_device: str = "auto",
        st_batch_size: int = 16,
        ticker_match_mode: str = "strict",
        recall_top_k_multiplier: int = 20,
        enable_signal_weighting: bool | None = None,
        signal_weighting_config: dict[str, Any] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.db_path = str(Path(db_path).expanduser())
        self.embed_backend = str(embed_backend or "sentence-transformers").strip()
        self.embed_model = str(embed_model or "bge-large-en-v1.5").strip()
        self.corpus_filter = str(corpus_filter or "").strip()
        self.exclude_corpus_filter = str(exclude_corpus_filter or "").strip()
        self.top_k = int(max(1, top_k))
        self.max_text_chars = int(max(200, max_text_chars))
        self.ollama_endpoint = str(ollama_endpoint or "http://127.0.0.1:11434").strip()
        self.hash_dim = int(max(8, hash_dim))
        self.st_device = str(st_device or "auto").strip()
        self.st_batch_size = int(max(1, st_batch_size))
        self.ticker_match_mode = str(ticker_match_mode or "strict").strip().lower()
        if self.ticker_match_mode not in {"soft", "strict"}:
            self.ticker_match_mode = "strict"
        self.recall_top_k_multiplier = int(max(1, recall_top_k_multiplier))
        yaml_signal_cfg = self._load_signal_weighting_from_cockpit_yaml()
        yaml_enable = yaml_signal_cfg.pop("enable_signal_weighting", None)
        default_signal_enable = str(self.corpus_filter or "").strip().lower() == "news"
        if enable_signal_weighting is not None:
            self.enable_signal_weighting = bool(enable_signal_weighting)
        elif yaml_enable is not None:
            self.enable_signal_weighting = bool(yaml_enable)
        else:
            self.enable_signal_weighting = default_signal_enable
        merged_signal_cfg = dict(DEFAULT_NEWS_WEIGHTING_CONFIG)
        for cfg_overrides in (yaml_signal_cfg, signal_weighting_config):
            if not isinstance(cfg_overrides, dict):
                continue
            for key, value in cfg_overrides.items():
                if key == "ticker_match_boosts" and isinstance(value, dict):
                    ticker_defaults = dict(merged_signal_cfg.get("ticker_match_boosts", {}))
                    ticker_defaults.update(value)
                    merged_signal_cfg["ticker_match_boosts"] = ticker_defaults
                else:
                    merged_signal_cfg[key] = value
        merged_signal_cfg["enable_signal_weighting"] = bool(self.enable_signal_weighting)
        self.news_weighting_config = merged_signal_cfg
        identity_path_value = str(self.news_weighting_config.get("ticker_identity_map_path") or "").strip()
        self.ticker_identity_config = (
            dict(self.news_weighting_config.get("ticker_identity"))
            if isinstance(self.news_weighting_config.get("ticker_identity"), dict)
            else {}
        )
        self.ticker_identity_map_path = self._resolve_ticker_identity_map_path(identity_path_value)
        self.ticker_identity_map = load_ticker_identity_map(str(self.ticker_identity_map_path))

        self._module: Any | None = None
        self._cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
        self._db_embedding_dim: int | None = None

    def _resolve_ticker_identity_map_path(self, raw_path: str) -> Path:
        txt = str(raw_path or "").strip()
        if not txt:
            return Path("")
        path = Path(txt).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.repo_root / path).resolve()

    def _load_signal_weighting_from_cockpit_yaml(self) -> dict[str, Any]:
        if str(self.corpus_filter or "").strip().lower() != "news":
            return {}
        if yaml is None:
            return {}

        config_path = (self.repo_root / "config" / "cockpit.yaml").resolve()
        if not config_path.exists() or not config_path.is_file():
            return {}
        try:
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
        if not isinstance(payload, dict):
            return {}
        rag_cfg = payload.get("rag")
        if not isinstance(rag_cfg, dict):
            return {}
        news_cfg = rag_cfg.get("news_context")
        if not isinstance(news_cfg, dict):
            return {}

        out: dict[str, Any] = {}
        if "enable_signal_weighting" in news_cfg:
            out["enable_signal_weighting"] = news_cfg.get("enable_signal_weighting")
        signal_cfg = news_cfg.get("signal_weighting")
        if isinstance(signal_cfg, dict):
            out.update(signal_cfg)
        return out

    @staticmethod
    def _boundary_match(text: str, token: str) -> bool:
        if not text or not token:
            return False
        return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE))

    @classmethod
    def _ticker_match_rank(cls, row: dict[str, Any], ticker: str, mod: Any) -> int:
        symbol = str(ticker or "").strip().upper()
        if not symbol:
            return 0

        ticker_blob = str(row.get("ticker") or "")
        try:
            if ticker_blob and bool(mod.ticker_blob_contains(ticker_blob, symbol)):
                return 1
        except Exception:
            if f"|{symbol}|" in f"|{ticker_blob.strip('|')}|":
                return 1

        title = str(row.get("title") or "")
        text = str(row.get("text") or "")
        payload = f"{title}\n{text[:2500]}"
        if re.search(rf"\bASX\s*[:\-]\s*{re.escape(symbol)}\b", payload, flags=re.IGNORECASE):
            return 2
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(symbol)}\.AX(?![A-Za-z0-9])", payload, flags=re.IGNORECASE):
            return 2
        if cls._boundary_match(payload, symbol):
            return 3
        return 0

    @staticmethod
    def _ticker_rank_to_signal_mode(rank: int) -> str:
        if rank <= 0:
            return "none"
        if rank == 1:
            return "exact"
        if rank == 2:
            return "strong"
        return "weak"

    @staticmethod
    def _extract_source_domain(row: dict[str, Any]) -> str:
        direct = str(row.get("source_domain") or "").strip().lower()
        if direct:
            return direct

        source = str(row.get("source") or "").strip().lower()
        if source and "." in source and " " not in source:
            return source.replace("www.", "", 1)

        url = str(row.get("url") or row.get("file") or "").strip()
        if url:
            try:
                host = urlparse(url).netloc.strip().lower()
            except Exception:
                host = ""
            if host:
                return host.replace("www.", "", 1)
        return ""

    def validate_runtime(self) -> None:
        db_path = Path(self.db_path).expanduser().resolve()
        if not db_path.exists() or not db_path.is_file():
            raise FileNotFoundError(f"qual context db not found: {db_path}")

        # Ensure retrieval script can be loaded before first query.
        self._load_module()
        self._validate_embedding_backend()
        self._validate_hash_embedding_compatibility(db_path)

    def _validate_embedding_backend(self) -> None:
        backend = str(self.embed_backend or "").strip().lower()
        if backend not in {"sentence-transformers", "hash", "ollama"}:
            raise ValueError(
                f"Unsupported RAG embed backend '{self.embed_backend}'. "
                "Expected one of: sentence-transformers, hash, ollama."
            )
        if backend == "sentence-transformers":
            try:
                import sentence_transformers  # type: ignore # noqa: F401
            except Exception as exc:
                raise RuntimeError(
                    "RAG embed backend 'sentence-transformers' is configured but dependency is missing. "
                    "Install with: pip install sentence-transformers"
                ) from exc
            st_mode = str(self.st_device or "auto").strip().lower()
            if st_mode in {"cuda_strict", "strict_cuda"}:
                try:
                    import torch  # type: ignore
                except Exception as exc:
                    raise RuntimeError(
                        "RAG CUDA strict mode requested but PyTorch is unavailable in this environment."
                    ) from exc
                if not torch.cuda.is_available() or int(torch.cuda.device_count()) <= 0:
                    raise RuntimeError(
                        "RAG CUDA strict mode requested (st_device=cuda_strict) but no CUDA GPU is visible to PyTorch."
                    )

    def _read_db_embedding_dim(self, db_path: Path) -> int | None:
        if self._db_embedding_dim is not None:
            return self._db_embedding_dim
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            row = cur.execute("SELECT embedding_json FROM context_chunks LIMIT 1").fetchone()
        except Exception:
            return None
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

        if not row or not row[0]:
            return None
        try:
            vec = json.loads(str(row[0]))
        except Exception:
            return None
        if not isinstance(vec, list):
            return None
        dim = len(vec)
        if dim <= 0:
            return None
        self._db_embedding_dim = int(dim)
        return self._db_embedding_dim

    def _validate_hash_embedding_compatibility(self, db_path: Path) -> None:
        backend = str(self.embed_backend or "").strip().lower()
        if backend != "hash":
            return
        db_dim = self._read_db_embedding_dim(db_path)
        if db_dim is None:
            return
        if db_dim != self.hash_dim:
            raise RuntimeError(
                "RAG hash embedding dimension mismatch: "
                f"db_dim={db_dim}, hash_dim={self.hash_dim}. "
                "Rebuild the qualitative context DB with matching hash_dim or use the backend used to build the DB."
            )

    def _load_module(self) -> Any:
        if self._module is not None:
            return self._module
        candidates = [
            (self.repo_root / "scripts" / "build_qualitative_context_db.py").resolve(),
            (self.repo_root.parent / "scripts" / "build_qualitative_context_db.py").resolve(),
            (Path.cwd() / "scripts" / "build_qualitative_context_db.py").resolve(),
        ]
        script_path = next((path for path in candidates if path.exists() and path.is_file()), None)
        if script_path is None:
            raise FileNotFoundError(
                "Qual context script not found in expected locations: "
                + ", ".join(str(path) for path in candidates)
            )
        spec = importlib.util.spec_from_file_location("build_qualitative_context_db", str(script_path))
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load module spec: {script_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._module = module
        return module

    def query(
        self,
        *,
        query: str,
        company: str,
        deep_mode: bool,
        top_k: int | None = None,
        doc_type_filter: str = "",
        date_from: str = "",
        date_to: str = "",
        ticker_filter: str = "",
        source_filter: str = "",
    ) -> dict[str, Any]:
        q = str(query or "").strip()
        comp = str(company or "").strip().upper()
        limit = int(top_k) if top_k is not None else self.top_k
        limit = int(max(1, limit))
        doc_type = str(doc_type_filter or "").strip()
        start_date = str(date_from or "").strip()
        end_date = str(date_to or "").strip()
        ticker = str(ticker_filter or "").strip().upper()
        source = str(source_filter or "").strip()
        deep_flag = bool(deep_mode)
        ticker_mode = self.ticker_match_mode
        is_soft_ticker_mode = bool(ticker and ticker_mode == "soft")
        recall_limit = limit * self.recall_top_k_multiplier if is_soft_ticker_mode else limit

        cache_key = (
            comp,
            ticker,
            source,
            q,
            limit,
            doc_type,
            start_date,
            end_date,
            deep_flag,
            ticker_mode,
            recall_limit,
        )
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] <= self.CACHE_TTL_SECONDS:
            return cached[1]

        payload: dict[str, Any] = {
            "ok": False,
            "query": q,
            "company": comp,
            "db_path": self.db_path,
            "embed_backend": self.embed_backend,
            "embed_model": self.embed_model,
            "corpus_filter": self.corpus_filter,
            "exclude_corpus_filter": self.exclude_corpus_filter,
            "doc_type_filter": doc_type,
            "date_from": start_date,
            "date_to": end_date,
            "ticker_filter": ticker,
            "source_filter": source,
            "top_k": limit,
            "ticker_match_mode": ticker_mode,
            "signal_weighting_enabled": bool(self.news_weighting_config.get("enable_signal_weighting", False)),
            "candidate_count": 0,
            "filtered_count": 0,
            "recall_top_k": recall_limit,
            "deep_mode": deep_flag,
            "hits": [],
            "error": None,
        }

        db_path = Path(self.db_path).expanduser().resolve()
        if not db_path.exists() or not db_path.is_file():
            payload["error"] = f"qual context db not found: {db_path}"
            return payload

        if not q or (not comp and not ticker):
            payload["error"] = "query and (company or ticker_filter) are required"
            return payload

        try:
            mod = self._load_module()
            self._validate_hash_embedding_compatibility(db_path)
            rows = mod.query_sqlite(
                db_path=db_path,
                query=q,
                backend=self.embed_backend,
                model_name=self.embed_model,
                ollama_endpoint=self.ollama_endpoint,
                hash_dim=self.hash_dim,
                st_device=self.st_device,
                st_batch_size=self.st_batch_size,
                company=comp,
                corpus_filter=self.corpus_filter,
                doc_type_filter=doc_type,
                date_from=start_date,
                date_to=end_date,
                top_k=recall_limit,
                ticker_filter="" if is_soft_ticker_mode else ticker,
                source_filter=source,
                exclude_corpus_filter=self.exclude_corpus_filter,
            )
            payload["candidate_count"] = len(rows)

            selected_rows: list[tuple[float, float, dict[str, Any], int, str, str, str]] = []
            if is_soft_ticker_mode:
                ranked: list[tuple[float, float, dict[str, Any], int, str, str, str]] = []
                for score, row in rows:
                    if not isinstance(row, dict):
                        continue
                    rank = self._ticker_match_rank(row=row, ticker=ticker, mod=mod)
                    score_f = float(score)
                    ticker_signal_mode = self._ticker_rank_to_signal_mode(rank)
                    source_domain = self._extract_source_domain(row)
                    identity_cfg = dict(self.ticker_identity_config)
                    identity_cfg["_source_domain"] = source_domain
                    identity_cfg["_source_is_au"] = bool(source_domain.endswith(".au"))
                    ticker_identity_strength = evaluate_ticker_identity_strength(
                        ticker=ticker,
                        title=str(row.get("title") or ""),
                        body=str(row.get("text") or ""),
                        identity_map=self.ticker_identity_map,
                        config=identity_cfg,
                    )
                    if rank <= 0 and ticker_identity_strength != "strong":
                        continue
                    final_score = compute_news_weighted_score(
                        semantic_score=score_f,
                        published_at=str(row.get("published_at") or row.get("doc_date") or ""),
                        ticker_match_mode=ticker_signal_mode,
                        title=str(row.get("title") or ""),
                        source_domain=source_domain,
                        config=self.news_weighting_config,
                        ticker_identity_strength=ticker_identity_strength,
                    )
                    ranked.append(
                        (
                            final_score,
                            score_f,
                            row,
                            rank,
                            ticker_signal_mode,
                            source_domain,
                            ticker_identity_strength,
                        )
                    )
                ranked.sort(key=lambda item: (-item[0], -item[1], item[3]))
                payload["filtered_count"] = len(ranked)
                selected_rows = ranked[:limit]
            else:
                ranked: list[tuple[float, float, dict[str, Any], int, str, str, str]] = []
                for score, row in rows:
                    if not isinstance(row, dict):
                        continue
                    score_f = float(score)
                    rank = self._ticker_match_rank(row=row, ticker=ticker, mod=mod) if ticker else 0
                    ticker_signal_mode = self._ticker_rank_to_signal_mode(rank)
                    source_domain = self._extract_source_domain(row)
                    identity_cfg = dict(self.ticker_identity_config)
                    identity_cfg["_source_domain"] = source_domain
                    identity_cfg["_source_is_au"] = bool(source_domain.endswith(".au"))
                    ticker_identity_strength = (
                        evaluate_ticker_identity_strength(
                            ticker=ticker,
                            title=str(row.get("title") or ""),
                            body=str(row.get("text") or ""),
                            identity_map=self.ticker_identity_map,
                            config=identity_cfg,
                        )
                        if ticker
                        else "none"
                    )
                    final_score = compute_news_weighted_score(
                        semantic_score=score_f,
                        published_at=str(row.get("published_at") or row.get("doc_date") or ""),
                        ticker_match_mode=ticker_signal_mode,
                        title=str(row.get("title") or ""),
                        source_domain=source_domain,
                        config=self.news_weighting_config,
                        ticker_identity_strength=ticker_identity_strength,
                    )
                    ranked.append(
                        (
                            final_score,
                            score_f,
                            row,
                            rank,
                            ticker_signal_mode,
                            source_domain,
                            ticker_identity_strength,
                        )
                    )
                ranked.sort(key=lambda item: (-item[0], -item[1], item[3]))
                selected_rows = ranked[:limit]
                payload["filtered_count"] = len(selected_rows)

            hits: list[dict[str, Any]] = []
            for final_score, score, row, ticker_rank, ticker_signal_mode, source_domain, ticker_identity_strength in selected_rows:
                text = str(row.get("text") or "")
                excerpt_chars = 2800 if deep_flag else self.max_text_chars
                hits.append(
                    {
                        "score": float(score),
                        "semantic_score": float(score),
                        "final_score": float(final_score),
                        "company": row.get("company"),
                        "corpus": row.get("corpus"),
                        "doc_type": row.get("doc_type"),
                        "doc_date": row.get("doc_date"),
                        "file": row.get("file"),
                        "section": row.get("section"),
                        "title": row.get("title"),
                        "published_at": row.get("published_at"),
                        "source_domain": source_domain,
                        "ticker": row.get("ticker"),
                        "ticker_signal_mode": ticker_signal_mode if ticker else None,
                        "ticker_identity_strength": ticker_identity_strength if ticker else None,
                        "ticker_match_rank": ticker_rank if is_soft_ticker_mode else None,
                        "text": text[:excerpt_chars],
                    }
                )
            payload["hits"] = hits
            payload["ok"] = True
        except Exception as exc:
            payload["error"] = str(exc)[:400]

        if len(self._cache) >= self.MAX_CACHE:
            oldest_key = min(self._cache.items(), key=lambda item: item[1][0])[0]
            self._cache.pop(oldest_key, None)
        self._cache[cache_key] = (now, payload)
        return payload
