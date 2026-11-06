"""
Tests for Controller Visualization Dashboards (Designs A, B, C).

These tests verify that the data endpoints the dashboards consume are healthy
and that the new /controller route is served correctly.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{(ROOT / 'data' / 'test_controller_dashboard.db').as_posix()}"
os.environ["APP_ENV"] = "testing"
os.environ["AUTO_CREATE_DB"] = "true"
os.environ["API_ACCESS_KEY"] = ""

from fastapi.testclient import TestClient
from app.main import app


def test_controller_dashboard_page_is_served():
    """The new Controller Visualization Dashboard HTML is available at /controller."""
    with TestClient(app) as client:
        response = client.get("/controller")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        body = response.text
        # Key markers from Designs A, B, C
        assert "Controller Visualization" in body or "Controller Dashboard" in body
        assert "dash-a" in body or "Executive Command" in body
        assert "dash-b" in body or "Investigation Focus" in body
        assert "dash-c" in body or "Plant Operational" in body
        assert "/api/v1" in body  # uses the existing API


def test_dashboard_a_data_contract_overview():
    """Design A (Executive Command) depends on /overview KPIs and priority exceptions."""
    with TestClient(app) as client:
        overview = client.get("/api/v1/overview")
        assert overview.status_code == 200
        data = overview.json()

        assert "kpis" in data
        kpis = data["kpis"]
        assert "open_exceptions" in kpis
        assert "financial_exposure" in kpis
        assert "root_causes_found" in kpis
        assert "evidence_complete" in kpis

        # Priority list used by the ranked table and exposure bars
        assert "priority_exceptions" in data or "data_quality_note" in data
        if "priority_exceptions" in data:
            assert isinstance(data["priority_exceptions"], list)


def test_dashboard_b_data_contract_investigation():
    """Design B (Investigation Focus) depends on /investigations/{id} for the three seeded cases."""
    with TestClient(app) as client:
        for case_id in ("case1", "case2", "case3"):
            inv = client.get(f"/api/v1/investigations/{case_id}")
            assert inv.status_code == 200, f"Investigation {case_id} failed"
            body = inv.json()

            # Core fields rendered by Design B
            assert "finding" in body or "title" in body
            assert "evidence" in body
            assert isinstance(body["evidence"], list)
            assert len(body["evidence"]) >= 1

            # Calculation object used in the calc panel
            assert "calculation" in body
            calc = body["calculation"]
            assert "formula" in calc or "result" in calc

            # Hypotheses and controls
            assert "hypotheses" in body
            assert "controls" in body


def test_dashboard_c_data_contract_exceptions_and_sources():
    """Design C (Plant Operational) uses exceptions list + data-sources."""
    with TestClient(app) as client:
        # Exceptions for material ranking and status distribution
        ex = client.get("/api/v1/exceptions?limit=50")
        assert ex.status_code == 200
        items = ex.json().get("items") or ex.json()
        assert isinstance(items, list)
        assert len(items) >= 3  # seeded cases exist

        for item in items[:3]:
            assert "impact_amount" in item
            assert "status" in item
            assert "priority" in item

        # Data sources panel
        ds = client.get("/api/v1/data-sources?limit=20")
        assert ds.status_code == 200
        # May be empty if no uploads yet; just ensure the endpoint is healthy
        body = ds.json()
        assert "items" in body or isinstance(body, list)


def test_dashboard_endpoints_are_consistent_with_seeded_demo():
    """Cross-check that the three seeded cases produce the numbers Design A expects."""
    with TestClient(app) as client:
        overview = client.get("/api/v1/overview").json()
        kpis = overview["kpis"]

        # Seeded demo has known baseline numbers (from existing test suite)
        assert kpis["open_exceptions"] >= 3
        assert kpis["financial_exposure"] > 0
        assert kpis["root_causes_found"] >= 1

        # case1 must be reachable for Design B default selection
        case1 = client.get("/api/v1/investigations/case1").json()
        assert case1.get("impact_amount") == 13400 or (case1.get("calculation") or {}).get("result") == 13400
