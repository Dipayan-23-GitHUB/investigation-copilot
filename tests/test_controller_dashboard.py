from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_controller_dashboard_returns_labelled_demo_finance_and_live_register_counts():
    with TestClient(app) as client:
        response = client.get("/api/v1/controller/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "DEMO_SYNTHETIC"
    assert "DEMO DATA" in payload["data_notice"]
    assert payload["source_window"]["periods"] == 12
    assert payload["kpis"]["revenue"] > 0
    assert payload["kpis"]["gross_profit"] > 0
    assert len(payload["revenue_trend"]) == 12
    assert payload["period_end"] == "2026-06-30"


def test_controller_dashboard_filters_one_month_and_entity():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/controller/dashboard",
            params={"from": "2025-07-01", "to": "2025-07-31", "entity": "Plant 100 — SFO"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source_window"]["periods"] == 1
    assert payload["period_start"] == "2025-07-01"
    assert payload["period_end"] == "2025-07-31"


def test_controller_dashboard_rejects_reversed_dates():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/controller/dashboard",
            params={"from": "2026-06-01", "to": "2025-07-01"},
        )
    assert response.status_code == 422
