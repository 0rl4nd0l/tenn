from __future__ import annotations

import json
from pathlib import Path

from app.services.marketplace_benchmark_service import (
    CENTRE_COM_SEED_PRODUCTS,
    OBS_SOURCE_LIVE_BROWSER,
    OBS_SOURCE_LIVE_HTTP,
    OBS_SOURCE_MANUAL_SNAPSHOT,
    OBS_SOURCE_SEED_FALLBACK,
    MarketplaceBenchmarkService,
)
from cockpit.storage.state import StateStore


def _state_store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


def test_refresh_uses_live_page_price_when_available(tmp_path: Path, monkeypatch) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceBenchmarkService(store)

    html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": "Centre Com Live Product",
            "offers": {
              "@type": "Offer",
              "priceCurrency": "AUD",
              "price": "1337.00"
            }
          }
        </script>
      </head>
      <body></body>
    </html>
    """

    monkeypatch.setattr(service, "_fetch_html", lambda _url: html)
    monkeypatch.setattr(service, "_fetch_html_via_browser", lambda _url: html)
    summary = service.refresh_centre_com_benchmarks()

    assert summary["live_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["fallback_observations_added"] == 0
    assert summary["price_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["observation_sources"][OBS_SOURCE_LIVE_HTTP] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["fetch_failures"] == []


def test_refresh_uses_browser_fallback_when_http_fetch_fails(
    tmp_path: Path, monkeypatch
) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceBenchmarkService(store)

    html = """
    <html>
      <head>
        <meta property="product:price:amount" content="1200.00" />
      </head>
      <body></body>
    </html>
    """

    monkeypatch.setattr(service, "_fetch_html", lambda _url: (_ for _ in ()).throw(RuntimeError("network down")))
    monkeypatch.setattr(service, "_fetch_html_via_browser", lambda _url: html)
    summary = service.refresh_centre_com_benchmarks()

    assert summary["live_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["fallback_observations_added"] == 0
    assert summary["observation_sources"][OBS_SOURCE_LIVE_BROWSER] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["fetch_failures"] == []


def test_refresh_uses_manual_snapshot_when_live_fetches_fail(
    tmp_path: Path, monkeypatch
) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceBenchmarkService(store)

    snapshot = {
        "items": [
            {
                "product_url": str(seed["product_url"]),
                "product_name": str(seed["product_name"]),
                "sku": str(seed["sku"]),
                "price": float(seed["price"]) + 10.0,
            }
            for seed in CENTRE_COM_SEED_PRODUCTS
        ]
    }
    snapshot_path = tmp_path / "centre_com_manual_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    monkeypatch.setenv("CENTRE_COM_MANUAL_SNAPSHOT_FILE", str(snapshot_path))
    monkeypatch.setattr(service, "_fetch_html", lambda _url: (_ for _ in ()).throw(RuntimeError("http blocked")))
    monkeypatch.setattr(service, "_fetch_html_via_browser", lambda _url: (_ for _ in ()).throw(RuntimeError("browser blocked")))

    summary = service.refresh_centre_com_benchmarks()

    assert summary["live_observations_added"] == 0
    assert summary["fallback_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["observation_sources"][OBS_SOURCE_MANUAL_SNAPSHOT] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["price_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert len(summary["fetch_failures"]) > 0


def test_refresh_falls_back_to_seed_prices_when_all_other_paths_fail(
    tmp_path: Path, monkeypatch
) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceBenchmarkService(store)

    monkeypatch.delenv("CENTRE_COM_MANUAL_SNAPSHOT_FILE", raising=False)
    monkeypatch.setattr(service, "_fetch_html", lambda _url: (_ for _ in ()).throw(RuntimeError("network down")))
    monkeypatch.setattr(service, "_fetch_html_via_browser", lambda _url: (_ for _ in ()).throw(RuntimeError("browser blocked")))

    summary = service.refresh_centre_com_benchmarks()

    assert summary["live_observations_added"] == 0
    assert summary["fallback_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["observation_sources"][OBS_SOURCE_SEED_FALLBACK] == len(CENTRE_COM_SEED_PRODUCTS)
    assert summary["price_observations_added"] == len(CENTRE_COM_SEED_PRODUCTS)
    assert len(summary["fetch_failures"]) > 0
