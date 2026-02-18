from __future__ import annotations

import httpx


class WebFetcher:
    def fetch_text(self, url: str, timeout: float = 20.0) -> str:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "FinancialEngineCockpit/1.0"})
            response.raise_for_status()
            return response.text[:8000]
