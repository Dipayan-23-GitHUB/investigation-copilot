from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from openpyxl import Workbook

from app.services import public_market_dashboard as market


def _world_bank_workbook() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Monthly Prices"
    # Representative Pink Sheet wide layout: year and month headers occupy
    # separate rows above Commodity / Unit.
    ws.append([None, None, None, 2025, 2025, 2026, 2026])
    ws.append([None, None, None, "September", "October", "January", "February"])
    ws.append(["Commodity", "Unit", None, None, None, None, None])
    ws.append(["Gold", "USD per troy ounce", None, 2650, 2690, 2725, 2750])
    ws.append(["Silver", "USD per troy ounce", None, 30.5, 31.2, 32.0, 33.1])
    stream = BytesIO()
    wb.save(stream)
    return stream.getvalue()


def test_world_bank_parser_handles_split_year_month_header():
    result = market.parse_world_bank_monthly_xlsx(_world_bank_workbook())
    assert result["gold"]["series"][-1] == {"date": "2026-02", "value": 2750.0}
    assert result["silver"]["series"][-1] == {"date": "2026-02", "value": 33.1}
    assert result["gold"]["unit"] == "USD per troy ounce"
    assert market._month_from_header(["2026M10"]) == "2026-10"
    assert market._month_from_header(["Jan-Dec 2025"]) is None



def test_fred_csv_parser_extracts_both_series_from_one_response(monkeypatch):
    content = (
        "observation_date,DCOILBRENTEU,DTWEXBGS\n"
        "2026-11-10,68.25,118.4\n"
        "2026-11-11,69.10,117.9\n"
    )

    def fake_get(*args, **kwargs):
        return httpx.Response(200, text=content, request=httpx.Request("GET", market.FRED_CSV_URL))

    monkeypatch.setattr(market.httpx, "get", fake_get)
    result = market._fetch_fred_csv()
    assert result["DCOILBRENTEU"][-1] == {"date": "2026-11-11", "value": 69.10}
    assert result["DTWEXBGS"][-1] == {"date": "2026-11-11", "value": 117.9}


def test_cache_suppresses_repeated_failed_provider_calls():
    market.clear_cache()
    calls = []

    def failing_loader():
        calls.append(1)
        raise RuntimeError("temporary upstream limit")

    with pytest.raises(market.PublicMarketError):
        market._cache_get("failing-feed", failing_loader, 3600)
    with pytest.raises(market.PublicMarketError):
        market._cache_get("failing-feed", failing_loader, 3600)
    assert len(calls) == 1


def test_stale_successful_cache_is_served_after_refresh_failure(monkeypatch):
    market.clear_cache()
    calls = []

    def successful_loader():
        calls.append("success")
        return {"sample": 123}

    value, stale = market._cache_get("stale-feed", successful_loader, 3600)
    assert value == {"sample": 123}
    assert stale is False
    market._CACHE["stale-feed"]["expires_at"] = 0

    def failing_loader():
        calls.append("failure")
        raise RuntimeError("upstream unavailable")

    value, stale = market._cache_get("stale-feed", failing_loader, 3600)
    assert value == {"sample": 123}
    assert stale is True
    assert calls == ["success", "failure"]


def test_market_dashboard_uses_public_sources_and_explains_restricted_feeds(monkeypatch):
    market.clear_cache()
    monkeypatch.setattr(market, "_fetch_fred_csv", lambda: {
        "DCOILBRENTEU": [
            {"date": "2026-11-10", "value": 68.0},
            {"date": "2026-11-11", "value": 69.0},
        ],
        "DTWEXBGS": [
            {"date": "2026-11-10", "value": 118.0},
            {"date": "2026-11-11", "value": 117.5},
        ],
    })
    monkeypatch.setattr(market, "_fetch_world_bank_metals", lambda: {
        "gold": {"unit": "USD per troy ounce", "series": [{"date": "2026-01", "value": 2700.0}, {"date": "2026-02", "value": 2750.0}]},
        "silver": {"unit": "USD per troy ounce", "series": [{"date": "2026-01", "value": 31.0}, {"date": "2026-02", "value": 33.0}]},
    })
    payload = market.public_market_dashboard()
    cards = payload["cards"]
    assert cards["brent"]["value"] == 69.0
    assert cards["usd_index"]["status"] == "available"
    assert cards["gold"]["value"] == 2750.0
    assert cards["silver"]["value"] == 33.0
    assert cards["us_stocks"]["status"] == "unavailable"
    assert cards["vix"]["status"] == "unavailable"
    assert cards["market_mood"]["status"] == "unavailable"
    assert payload["available_cards"] == 4


def test_public_market_dashboard_endpoint_uses_low_cost_public_adapter(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import market as market_router

    fixture = {
        "cards": {"brent": {"status": "available", "value": 70.0}},
        "source": "FRED/EIA + World Bank Pink Sheet",
        "frequency": "Daily and monthly reference observations",
        "generated_at": "2026-11-12T00:00:00+00:00",
        "available_cards": 4,
        "notes": [],
    }
    monkeypatch.setattr(market_router, "public_market_dashboard", lambda: fixture)
    with TestClient(app) as client:
        response = client.get("/api/v1/market/dashboard")
    assert response.status_code == 200
    assert response.json()["source"] == "FRED/EIA + World Bank Pink Sheet"
