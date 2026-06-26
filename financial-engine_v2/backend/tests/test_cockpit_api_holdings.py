from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.routes import cockpit_api
from app.routes.cockpit_api import router
from app.services.cockpit_service import CockpitService
from cockpit.storage.state import StateStore


def _fake_service(tmp_path: Path) -> SimpleNamespace:
    state_store = StateStore(str(tmp_path / "state.db"))
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        state_store=state_store,
        artifact_store=SimpleNamespace(logs_dir=logs_dir),
    )


def test_holdings_crud_api_round_trip(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/holdings",
        json={
            "ticker": "bhp",
            "quantity": 100,
            "avg_cost": 42.5,
            "account_label": "Broker",
            "note": "starter position",
        },
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["ticker"] == "BHP"
    assert created["quantity"] == 100.0
    assert created["avg_cost"] == 42.5
    assert created["account_label"] == "Broker"
    assert created["note"] == "starter position"
    holding_id = created["holding_id"]

    list_response = client.get("/api/cockpit/holdings")
    assert list_response.status_code == 200
    listed = list_response.json()["items"]
    assert len(listed) == 1
    assert listed[0]["holding_id"] == holding_id

    patch_response = client.patch(
        f"/api/cockpit/holdings/{holding_id}",
        json={
            "quantity": 125,
            "avg_cost": 41.2,
            "account_label": "Brokerage A",
            "note": "trimmed then rebuilt",
        },
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["quantity"] == 125.0
    assert updated["avg_cost"] == 41.2
    assert updated["account_label"] == "Brokerage A"
    assert updated["note"] == "trimmed then rebuilt"

    clear_response = client.patch(
        f"/api/cockpit/holdings/{holding_id}",
        json={"note": None, "account_label": None},
    )
    assert clear_response.status_code == 200
    cleared = clear_response.json()
    assert cleared["note"] is None
    assert cleared["account_label"] is None

    delete_response = client.delete(f"/api/cockpit/holdings/{holding_id}")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True, "holding_id": holding_id}

    after_delete = client.get("/api/cockpit/holdings")
    assert after_delete.status_code == 200
    assert after_delete.json()["items"] == []


@pytest.mark.parametrize(
    ("method", "path", "json_body"),
    [
        ("get", "/api/cockpit/holdings", None),
        ("post", "/api/cockpit/holdings", {"ticker": "BHP", "quantity": 10}),
        ("patch", "/api/cockpit/holdings/existing", {"quantity": 20}),
        ("delete", "/api/cockpit/holdings/existing", None),
    ],
)
@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_holdings_routes_require_api_key_when_configured(
    tmp_path,
    monkeypatch,
    method,
    path,
    json_body,
    headers,
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings,
        "local_api_key",
        "local-secret",
        raising=False,
    )
    existing_id = fake_service.state_store.add_holding(
        ticker="BHP",
        quantity=10,
        avg_cost=42.5,
    )
    path = path.replace("existing", existing_id)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    request = getattr(client, method)
    if json_body is None:
        response = request(path, headers=headers)
    else:
        response = request(path, headers=headers, json=json_body)

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    rows = fake_service.state_store.list_holdings()
    assert len(rows) == 1
    assert rows[0]["holding_id"] == existing_id
    assert rows[0]["ticker"] == "BHP"
    assert rows[0]["quantity"] == 10.0


def test_holdings_routes_accept_correct_api_key_when_configured(
    tmp_path,
    monkeypatch,
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings,
        "local_api_key",
        "local-secret",
        raising=False,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)
    headers = {"X-API-Key": "local-secret"}

    create_response = client.post(
        "/api/cockpit/holdings",
        headers=headers,
        json={"ticker": "BHP", "quantity": 10, "avg_cost": 42.5},
    )
    assert create_response.status_code == 200
    holding_id = create_response.json()["holding_id"]

    list_response = client.get("/api/cockpit/holdings", headers=headers)
    assert list_response.status_code == 200
    assert [item["holding_id"] for item in list_response.json()["items"]] == [
        holding_id
    ]

    patch_response = client.patch(
        f"/api/cockpit/holdings/{holding_id}",
        headers=headers,
        json={"quantity": 25},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["quantity"] == 25.0

    delete_response = client.delete(
        f"/api/cockpit/holdings/{holding_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True, "holding_id": holding_id}


def test_holdings_update_unknown_id_returns_404(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    response = client.patch(
        "/api/cockpit/holdings/does-not-exist",
        json={"note": "x"},
    )
    assert response.status_code == 404


def test_holdings_list_includes_live_market_value(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_live_price_snapshot_for_holding",
        lambda ticker, market_exchange: (
            {
                "current_price": 50.25,
                "price_currency": "AUD",
                "price_as_of": "2026-04-22T10:00:00+00:00",
                "market_exchange": market_exchange or "ASX",
            }
            if str(ticker).upper() == "BHP"
            else None
        ),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/holdings",
        json={
            "ticker": "bhp",
            "quantity": 100,
            "avg_cost": 42.5,
            "cost_currency": "AUD",
            "market_exchange": "asx",
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/cockpit/holdings")
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["ticker"] == "BHP"
    assert item["market_exchange"] == "ASX"
    assert item["current_price"] == 50.25
    assert item["market_value"] == 5025.0
    assert item["unrealized_pnl"] == 775.0


def test_holdings_unrealized_pnl_hidden_on_currency_mismatch(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_live_price_snapshot_for_holding",
        lambda ticker, market_exchange: (
            {
                "current_price": 284.49,
                "price_currency": "USD",
                "price_as_of": "2026-04-22T10:00:00+00:00",
                "market_exchange": market_exchange or "NASDAQ",
            }
            if str(ticker).upper() == "AMD"
            else None
        ),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/holdings",
        json={
            "ticker": "amd",
            "quantity": 10,
            "avg_cost": 130,
            "cost_currency": "AUD",
            "market_exchange": "NASDAQ",
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/cockpit/holdings")
    assert list_response.status_code == 200
    item = list_response.json()["items"][0]
    assert item["current_price"] == 284.49
    assert item["market_value"] == 2844.9
    assert item["unrealized_pnl"] is None
    assert "currency mismatch" in str(item["valuation_warning"]).lower()


def test_holdings_unrealized_pnl_requires_known_currencies(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api,
        "_fetch_live_price_snapshot_for_holding",
        lambda ticker, market_exchange: (
            {
                "current_price": 56.17,
                "price_currency": "AUD",
                "price_as_of": "2026-04-22T10:00:00+00:00",
                "market_exchange": market_exchange or "ASX",
            }
            if str(ticker).upper() == "BHP"
            else None
        ),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    create_response = client.post(
        "/api/cockpit/holdings",
        json={
            "ticker": "BHP",
            "quantity": 100,
            "avg_cost": 42.5,
            "market_exchange": "ASX",
        },
    )
    assert create_response.status_code == 200

    list_response = client.get("/api/cockpit/holdings")
    assert list_response.status_code == 200
    item = list_response.json()["items"][0]
    assert item["current_price"] == 56.17
    assert item["market_value"] == 5617.0
    assert item["unrealized_pnl"] is None
    assert "both cost currency and live price currency" in str(item["valuation_warning"]).lower()


def test_holdings_csv_attachment_import(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = (
        "ticker,quantity,avg_cost,account_label,note\n"
        "BHP,100,43.2,Broker A,core\n"
        "CBA,50,118.5,Broker B,trim candidate\n"
    )
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "holdings.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["file_kind"] == "holdings_csv"
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0

    holdings = client.get("/api/cockpit/holdings").json()["items"]
    assert len(holdings) == 2
    assert {row["ticker"] for row in holdings} == {"BHP", "CBA"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_holdings_csv_attachment_upload_requires_api_key_before_import(
    tmp_path, monkeypatch, headers
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings, "local_api_key", "local-secret", raising=False
    )

    add_holding_calls: list[dict[str, object]] = []

    def fail_add_holding(**row: object) -> None:
        add_holding_calls.append(row)
        raise AssertionError("add_holding must not run for rejected attachment uploads")

    monkeypatch.setattr(fake_service.state_store, "add_holding", fail_add_holding)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = "ticker,quantity,avg_cost\nBHP,100,43.2\n"
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        headers=headers,
        json={
            "filename": "holdings.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    assert add_holding_calls == []
    assert fake_service.state_store.list_holdings() == []


def test_holdings_csv_attachment_upload_accepts_correct_api_key_when_configured(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings, "local_api_key", "local-secret", raising=False
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = "ticker,quantity,avg_cost\nBHP,100,43.2\n"
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        headers={"X-API-Key": "local-secret"},
        json={
            "filename": "holdings.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_kind"] == "holdings_csv"
    assert payload["imported_count"] == 1
    holdings = client.get(
        "/api/cockpit/holdings",
        headers={"X-API-Key": "local-secret"},
    ).json()["items"]
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "BHP"


def test_holdings_csv_derives_avg_cost_from_value_and_capital_gain(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = (
        "symbol,quantity,value,capital_gain\n"
        "EIQ,5700,6526.5,5370.52\n"
        "CSL,22,2904,-1979.95\n"
    )
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "holdings-derived-cost.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 2

    holdings = client.get("/api/cockpit/holdings").json()["items"]
    by_ticker = {row["ticker"]: row for row in holdings}
    assert by_ticker["EIQ"]["avg_cost"] == pytest.approx(0.2028035087719298)
    assert by_ticker["CSL"]["avg_cost"] == pytest.approx(221.99772727272727)


def test_holdings_xlsx_attachment_import(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["ticker", "quantity", "avg_cost", "account_label", "note"])
    sheet.append(["BHP", 100, 43.2, "Broker A", "core"])
    sheet.append(["CBA", 50, 118.5, "Broker B", "trim candidate"])
    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "holdings.xlsx",
            "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content_base64": encoded,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["file_kind"] == "holdings_csv"
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0

    holdings = client.get("/api/cockpit/holdings").json()["items"]
    assert len(holdings) == 2
    assert {row["ticker"] for row in holdings} == {"BHP", "CBA"}


def test_trades_csv_attachment_import_aggregates_positions(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = (
        "ticker,side,quantity,price,trade_date,account_label\n"
        "BHP,buy,100,40,2026-01-10,Broker A\n"
        "BHP,buy,50,44,2026-01-12,Broker A\n"
        "BHP,sell,30,48,2026-01-20,Broker A\n"
        "CBA,buy,10,120,2026-01-05,Broker B\n"
    )
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "trades.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
            "csv_profile": "trades",
            "csv_strict": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["file_kind"] == "holdings_csv"
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0

    holdings = client.get("/api/cockpit/holdings").json()["items"]
    assert len(holdings) == 2
    by_ticker = {row["ticker"]: row for row in holdings}
    assert by_ticker["BHP"]["quantity"] == 120.0
    assert by_ticker["BHP"]["avg_cost"] == 41.333333333333336
    assert by_ticker["CBA"]["quantity"] == 10.0
    assert by_ticker["CBA"]["avg_cost"] == 120.0


def test_strict_trades_profile_rejects_missing_required_columns(
    tmp_path, monkeypatch
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    csv_text = (
        "ticker,quantity,price\n"
        "BHP,100,40\n"
    )
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "trades.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
            "csv_profile": "trades",
            "csv_strict": True,
        },
    )
    assert response.status_code == 400
    assert "missing columns: side" in response.json()["detail"]

    holdings = client.get("/api/cockpit/holdings").json()["items"]
    assert holdings == []


def test_attachment_upload_rejects_oversized_payload(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(cockpit_api, "_MAX_CHAT_ATTACHMENT_BYTES", 8)

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    encoded = base64.b64encode(b"123456789").decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        json={
            "filename": "holdings.csv",
            "mime_type": "text/csv",
            "content_base64": encoded,
        },
    )

    assert response.status_code == 413
    assert "attachment exceeds" in response.json()["detail"]
    assert client.get("/api/cockpit/holdings").json()["items"] == []


def test_pdf_attachment_upload_creates_attached_source(tmp_path, monkeypatch) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings, "local_api_key", "local-secret", raising=False
    )
    monkeypatch.setattr(
        cockpit_api,
        "_extract_pdf_text",
        lambda _bytes: (
            "Strategy update: Operating leverage improved and free cash flow expanded. "
            "Risk controls include liquidity buffers and monthly stress testing."
        ),
    )
    monkeypatch.setattr(
        cockpit_api,
        "_stage_uploaded_pdf_chunks",
        lambda **_kwargs: ("market_commentary:strategy-update:abc123", 3),
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    pdf_bytes = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"

    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        headers={"X-API-Key": "local-secret"},
        json={
            "filename": "strategy-update.pdf",
            "mime_type": "application/pdf",
            "content_base64": encoded,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["file_kind"] == "strategy_pdf"
    assert payload["source_id"]
    assert payload["chunks_staged"] >= 1
    assert isinstance(payload["key_points"], list)


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_pdf_attachment_upload_requires_api_key_before_staging(
    tmp_path, monkeypatch, headers
) -> None:
    fake_service = _fake_service(tmp_path)
    monkeypatch.setattr(
        CockpitService, "get_instance", classmethod(lambda cls: fake_service)
    )
    monkeypatch.setattr(
        cockpit_api.settings, "local_api_key", "local-secret", raising=False
    )

    staged_calls: list[dict[str, object]] = []

    def fail_stage_uploaded_pdf_chunks(**kwargs: object) -> tuple[str, int]:
        staged_calls.append(kwargs)
        raise AssertionError(
            "_stage_uploaded_pdf_chunks must not run for rejected attachment uploads"
        )

    monkeypatch.setattr(
        cockpit_api, "_extract_pdf_text", lambda _bytes: "extracted text"
    )
    monkeypatch.setattr(
        cockpit_api,
        "_stage_uploaded_pdf_chunks",
        fail_stage_uploaded_pdf_chunks,
    )

    app = FastAPI()
    app.include_router(router, prefix="/api/cockpit")
    client = TestClient(app)

    pdf_bytes = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    response = client.post(
        "/api/cockpit/chat/attachments/upload",
        headers=headers,
        json={
            "filename": "strategy-update.pdf",
            "mime_type": "application/pdf",
            "content_base64": encoded,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"
    assert staged_calls == []
