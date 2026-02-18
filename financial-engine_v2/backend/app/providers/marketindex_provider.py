import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from app.providers.asx_provider import DiscoveredDoc, _classify, _try_period_end


def _parse_marketindex_datetime(date_text, time_text):
    if not date_text:
        return None
    value = (f"{date_text} {time_text or ''}").strip()
    for fmt in ("%d/%m/%y %I:%M%p", "%d/%m/%Y %I:%M%p", "%d/%m/%y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(value.replace(" ", ""), fmt.replace(" ", ""))
            return parsed.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


class MarketIndexProvider:
    def __init__(self, announcements_file):
        self.announcements_file = Path(announcements_file)

    def discover(self, ticker, start, end) -> List[DiscoveredDoc]:
        if not self.announcements_file.exists():
            return []

        payload = json.loads(self.announcements_file.read_text())
        announcements = payload.get("announcements", [])
        ticker = ticker.upper()

        seen = set()
        docs = []
        for announcement in announcements:
            if (announcement.get("ticker") or "").upper() != ticker:
                continue

            source_url = announcement.get("link")
            if not source_url:
                continue
            if source_url in seen:
                continue

            published_at = _parse_marketindex_datetime(announcement.get("date"), announcement.get("time"))
            if published_at and (published_at < start or published_at > end):
                continue

            title = (announcement.get("heading") or "").strip() or "MarketIndex Announcement"
            doc_class, doc_subtype = _classify(title)
            docs.append(
                DiscoveredDoc(
                    ticker=ticker,
                    exchange="ASX",
                    doc_class=doc_class,
                    doc_subtype=doc_subtype,
                    title=title,
                    source_url=source_url,
                    published_at=published_at,
                    period_end=_try_period_end(title),
                )
            )
            seen.add(source_url)
        return docs
