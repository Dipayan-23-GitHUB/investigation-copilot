from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import market_data


def _response(payload):
    return httpx.Response(200, json=payload, request=httpx.Request("GET", market_data.BASE_URL))


def test_market_endpoints_require_provider_key(monkeypatch):
    monkeypatch.setattr(market_data.settings, "alpha_vantage_api_key", "")
    market_data.clear_market_cache()
    with TestClient(app) as client:
        response = client.get("/api/v1/market/equity", params={"symbol": "IBM"})
        assert response.status_code == 503
        assert "MARKET_DATA_API_KEY" in response.json()["detail"]


def test_equity_history_normalizes_daily_series_and_caches(monkeypatch):
    monkeypatch.setattr(market_data.settings, "alpha_vantage_api_key", "test-key")
    market_data.clear_market_cache()
    calls = []

    def fake_get(url, params, timeout):
        calls.append(params)
        return _response({
            "Meta Data": {"3. Last Refreshed": "2026-11-05", "5. Time Zone": "US/Eastern"},
            "Time Series (Daily)": {
                "2026-11-05": {"1. open": "100", "2. high": "110", "3. low": "95", "4. close": "108", "5. volume": "1200"},
                "2026-11-04": {"1. open": "90", "2. high": "105", "3. low": "89", "4. close": "100", "5. volume": "1100"},
            },
        })

    monkeypatch.setattr(market_data.httpx, "get", fake_get)
    first = market_data.equity_history("ibm")
    second = market_data.equity_history("IBM")
    assert first["symbol"] == "IBM"
    assert first["latest"]["close"] == 108.0
    assert round(first["change_percent"], 2) == 8.0
    assert len(first["series"]) == 2
    assert second == first
    assert len(calls) == 1


def test_metals_overview_parses_daily_and_monthly_data(monkeypatch):
    monkeypatch.setattr(market_data.settings, "alpha_vantage_api_key", "test-key")
    market_data.clear_market_cache()

    def fake_get(url, params, timeout):
        fn = params["function"]
        if fn == "GOLD_SILVER_HISTORY":
            symbol = params["symbol"]
            base = 2000 if symbol == "GOLD" else 25
            return _response({"Meta Data": {"Unit": "USD per troy ounce"}, "data": [
                {"date": "2026-11-04", "value": str(base)},
                {"date": "2026-11-05", "value": str(base + 10)},
            ]})
        base = 9000 if fn == "COPPER" else 2500
        return _response({"Meta Data": {"Unit": "USD per metric ton"}, "data": [
            {"date": "2026-09", "value": str(base)},
            {"date": "2026-10", "value": str(base + 100)},
        ]})

    monkeypatch.setattr(market_data.httpx, "get", fake_get)
    result = market_data.metals_overview()
    assert result["count"] == 4
    by_symbol = {item["symbol"]: item for item in result["items"]}
    assert by_symbol["GOLD"]["latest"]["value"] == 2010.0
    assert by_symbol["COPPER"]["interval"] == "monthly"
    assert by_symbol["ALUMINUM"]["latest"]["date"] == "2026-10"
    assert not result["errors"]


def test_equity_symbol_validation(monkeypatch):
    monkeypatch.setattr(market_data.settings, "alpha_vantage_api_key", "test-key")
    market_data.clear_market_cache()
    with TestClient(app) as client:
        response = client.get("/api/v1/market/equity", params={"symbol": "IBM/../bad"})
        assert response.status_code == 422
