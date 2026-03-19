from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

UTC = dt.timezone.utc
WS_RE = re.compile(r"\s+")
ALNUM_RE = re.compile(r"[a-z0-9]+")
COMPACT_UTC_RE = re.compile(r"^\d{14}$")
COMPACT_T_UTC_RE = re.compile(r"^\d{8}T\d{6}Z$")
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TRACKING_PARAM_EXACT = {
    "amp",
    "amp_js_v",
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "mkt_tok",
    "ref",
    "ref_src",
    "ref_url",
    "spm",
    "yclid",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
}


def now_utc_iso() -> str:
    return dt.datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_space(value: Any) -> str:
    return WS_RE.sub(" ", str(value or "").replace("\r", " ").replace("\n", " ")).strip()


def normalize_text(value: Any) -> str:
    txt = normalize_space(value).lower()
    txt = re.sub(r"[^a-z0-9 ]+", " ", txt)
    return WS_RE.sub(" ", txt).strip()


def _dt_to_utc_z(value: dt.datetime) -> str:
    ts = value
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    else:
        ts = ts.astimezone(UTC)
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_unix_timestamp(value: str) -> Optional[str]:
    if not value or not value.lstrip("-").isdigit():
        return None
    try:
        raw = int(value)
    except Exception:
        return None
    # Heuristic: 13 digits usually means milliseconds.
    if abs(raw) >= 10**12:
        raw = int(raw / 1000.0)
    try:
        ts = dt.datetime.fromtimestamp(raw, tz=UTC)
    except Exception:
        return None
    return _dt_to_utc_z(ts)


def parse_datetime_utc(value: Any) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None

    if COMPACT_UTC_RE.fullmatch(raw):
        try:
            ts = dt.datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
            return _dt_to_utc_z(ts)
        except ValueError:
            return None

    if COMPACT_T_UTC_RE.fullmatch(raw):
        try:
            ts = dt.datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
            return _dt_to_utc_z(ts)
        except ValueError:
            return None

    unix = _parse_unix_timestamp(raw)
    if unix:
        return unix

    if DATE_ONLY_RE.fullmatch(raw):
        try:
            ts = dt.datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC)
            return _dt_to_utc_z(ts)
        except ValueError:
            return None

    # ISO-8601 variants.
    candidate = raw.replace("/", "-")
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    iso_candidates = [candidate]
    if " " in candidate and "T" not in candidate:
        iso_candidates.append(candidate.replace(" ", "T"))
    for item in iso_candidates:
        try:
            ts = dt.datetime.fromisoformat(item)
            return _dt_to_utc_z(ts)
        except ValueError:
            pass

    # RFC2822 / RFC1123 style.
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
        if parsed is not None:
            return _dt_to_utc_z(parsed)
    except Exception:
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            ts = dt.datetime.strptime(raw, fmt)
            return _dt_to_utc_z(ts)
        except ValueError:
            continue
    return None


def utc_date(value: str) -> str:
    ts = parse_datetime_utc(value)
    if not ts:
        return ""
    return ts.split("T", 1)[0]


def should_drop_query_param(key: str) -> bool:
    low = str(key or "").strip().lower()
    if not low:
        return True
    if low in TRACKING_PARAM_EXACT:
        return True
    if low.startswith("utm_"):
        return True
    if low.startswith("amp_"):
        return True
    if low.startswith("ga_"):
        return True
    return False


def canonicalize_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    raw = raw.replace(" ", "")
    if "://" not in raw and not raw.startswith("//"):
        raw = "https://" + raw
    split = urlsplit(raw)
    scheme = (split.scheme or "https").lower()
    host = (split.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    port = split.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = host if port is None else f"{host}:{port}"
    path = split.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    params: List[Tuple[str, str]] = []
    for key, val in parse_qsl(split.query, keep_blank_values=True):
        if should_drop_query_param(key):
            continue
        params.append((key, val))
    params.sort(key=lambda item: (item[0].lower(), item[1]))
    query = urlencode(params, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def sha256_hex(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def sha1_hex(value: str) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()


def compute_exact_hash(title: str, description: str) -> str:
    payload = normalize_text(f"{title}\n{description}")
    return sha256_hex(payload)


def simhash64(text: str) -> str:
    tokens = ALNUM_RE.findall(normalize_text(text))
    if not tokens:
        return "0" * 16
    vec = [0] * 64
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bits = int.from_bytes(digest[:8], byteorder="big", signed=False)
        for idx in range(64):
            vec[idx] += 1 if ((bits >> idx) & 1) else -1
    out = 0
    for idx, score in enumerate(vec):
        if score >= 0:
            out |= (1 << idx)
    return f"{out:016x}"


def compute_near_hash(title: str, description: str, body: str) -> str:
    payload = normalize_text(f"{title}\n{description}\n{body[:3000]}")
    return simhash64(payload)


def parse_extra_fields(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return {}
        try:
            parsed = json.loads(txt)
        except Exception:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def parse_ticker_blob(value: Any) -> List[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    if "|" in raw:
        parts = [item for item in raw.split("|") if item.strip()]
    else:
        parts = [item for item in re.split(r"[,\s;/]+", raw) if item.strip()]
    out = sorted(
        {
            re.sub(r"[^A-Za-z0-9]", "", item.strip().upper())
            for item in parts
            if re.sub(r"[^A-Za-z0-9]", "", item.strip().upper())
        }
    )
    return out


def serialize_ticker_blob(values: Sequence[str]) -> str:
    ordered = sorted(
        {
            re.sub(r"[^A-Za-z0-9]", "", str(item or "").strip().upper())
            for item in values
            if re.sub(r"[^A-Za-z0-9]", "", str(item or "").strip().upper())
        }
    )
    if not ordered:
        return ""
    return "|" + "|".join(ordered) + "|"


def load_ticker_universe(path: Path) -> List[str]:
    if not path.exists():
        raise RuntimeError(f"Ticker universe not found: {path}")
    out: List[str] = []
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.split("#", 1)[0].strip()
        if not raw:
            continue
        sym = re.sub(r"[^A-Za-z0-9]", "", raw.upper())
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def day_windows(from_day: str, to_day: str) -> Iterator[Tuple[str, str]]:
    start = dt.date.fromisoformat(from_day)
    end = dt.date.fromisoformat(to_day)
    if start > end:
        raise ValueError("--from must be <= --to")
    cur = start
    while cur <= end:
        s = dt.datetime.combine(cur, dt.time.min, tzinfo=UTC)
        e = dt.datetime.combine(cur, dt.time.max.replace(microsecond=0), tzinfo=UTC)
        yield _dt_to_utc_z(s), _dt_to_utc_z(e)
        cur += dt.timedelta(days=1)
