from __future__ import annotations

from types import SimpleNamespace

from app.services.ebay_sold_scanner import EbaySoldScanner, _sold_search_queries


def test_sold_search_queries_include_pro_ace_aliases() -> None:
    queries = _sold_search_queries(
        {
            "canonical_key": "motherboard-asus-pro-ws-x570-ace-am4",
            "brand": "ASUS",
            "model_family": "Pro WS X570-ACE",
            "variant": "AM4 X570",
            "aliases": [
                "ASUS Pro WS X570-ACE",
                "PRO-WS-X570-ACE",
                "WS X570-ACE",
            ],
        }
    )

    assert queries == [
        "ASUS Pro WS X570-ACE AM4 X570",
        "Pro WS X570-ACE AM4 X570",
        "ASUS Pro WS X570-ACE",
        "PRO-WS-X570-ACE",
    ]


def test_scrape_sold_items_sync_wraps_async_method(monkeypatch) -> None:
    scanner = EbaySoldScanner(SimpleNamespace())
    calls: list[dict[str, object]] = []

    async def fake_scrape_sold_items(**kwargs):
        calls.append(kwargs)
        return {"ok": True, **kwargs}

    monkeypatch.setattr(scanner, "scrape_sold_items", fake_scrape_sold_items)

    result = scanner.scrape_sold_items_sync(
        tracked_product_id="tp_pro_ace",
        query="ASUS Pro WS X570-ACE",
    )

    assert result["ok"] is True
    assert calls == [
        {
            "tracked_product_id": "tp_pro_ace",
            "query": "ASUS Pro WS X570-ACE",
            "log": None,
        }
    ]
