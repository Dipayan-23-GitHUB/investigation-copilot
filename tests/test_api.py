import os
from pathlib import Path

# Isolate test state from the developer's normal local database before importing the app.
ROOT = Path(__file__).resolve().parents[1]
os.environ["DATABASE_URL"] = f"sqlite:///{(ROOT / 'data' / 'test_api.db').as_posix()}"
os.environ["APP_ENV"] = "testing"
os.environ["AUTO_CREATE_DB"] = "true"
os.environ["API_ACCESS_KEY"] = ""

from fastapi.testclient import TestClient
from app.main import app


def test_catalog_has_12_source_ledger_modules():
    with TestClient(app) as client:
        response = client.get("/api/v1/catalog/modules")
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 12
        catalog = client.get("/api/v1/catalog/source-objects")
        assert catalog.status_code == 200
        assert catalog.json()["count"] >= 50
        assert {x["key"] for x in body["items"]} >= {"plant-controller", "cost-accounting", "accounts-payable", "ar-credit"}


def test_overview_and_exception_details():
    with TestClient(app) as client:
        overview = client.get("/api/v1/overview")
        assert overview.status_code == 200
        kpis = overview.json()["kpis"]
        assert kpis["open_exceptions"] == 8
        assert round(kpis["financial_exposure"], 2) == 184300.00
        assert kpis["root_causes_found"] == 5
        assert kpis["evidence_complete"] == 4
        case = client.get("/api/v1/exceptions/case1")
        assert case.status_code == 200
        assert case.json()["impact_amount"] == 13400
        evidence = client.get("/api/v1/exceptions/case1/evidence")
        assert evidence.status_code == 200
        assert evidence.json()["count"] == 4


def test_upload_source_ledger_plant_workbook():
    sample = ROOT / "sample_data" / "03-plant-controller-sample-extract.xlsx"
    with TestClient(app) as client:
        with sample.open("rb") as handle:
            response = client.post("/api/v1/ingestions", data={"module_key":"plant-controller", "header_row":"5"}, files={"file":(sample.name, handle, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["row_count"] > 0
        assert result["sheet_count"] == 1
        source_id = result["id"]
        sheets = client.get(f"/api/v1/data-sources/{source_id}/sheets")
        assert sheets.status_code == 200
        assert sheets.json()["items"][0]["source_object"] == "SAP MBEW material valuation"
        records = client.get(f"/api/v1/data-sources/{source_id}/rows", params={"sheet_name":sheets.json()["items"][0]["sheet_name"],"limit":5})
        assert records.status_code == 200
        assert len(records.json()["items"]) > 0


def test_action_create_and_update():
    with TestClient(app) as client:
        created = client.post("/api/v1/actions", json={"title":"Validate supplier price condition","owner":"Procurement","status":"open","action_type":"investigation","exception_id":"case1"})
        assert created.status_code == 201, created.text
        action_id = created.json()["id"]
        updated = client.patch(f"/api/v1/actions/{action_id}", json={"status":"in_progress"})
        assert updated.status_code == 200
        assert updated.json()["status"] == "in_progress"


def test_groq_is_not_called_when_api_key_is_missing():
    with TestClient(app) as client:
        response = client.post("/api/v1/copilot/chat", json={"exception_id":"case1","message":"What proves the amount?"})
        assert response.status_code == 503
        assert "GROQ_API_KEY" in response.json()["detail"]


def test_frontend_is_served_and_ui_session_uses_http_only_cookie(monkeypatch):
    from app import main

    monkeypatch.setattr(main.settings, "api_access_key", "test-shared-key")
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "authGate" in page.text
        assert "priorityExceptionBody" in page.text
        assert "test-shared-key" not in page.text

        unauthenticated = client.get("/api/v1/overview")
        assert unauthenticated.status_code == 401

        login = client.post("/ui/session", json={"api_key": "wrong-key"})
        assert login.status_code == 401

        login = client.post("/ui/session", json={"api_key": "test-shared-key"})
        assert login.status_code == 200
        cookie_header = login.headers.get("set-cookie", "")
        assert "HttpOnly" in cookie_header
        assert "SameSite=strict" in cookie_header
        assert "test-shared-key" not in cookie_header

        authenticated = client.get("/api/v1/overview")
        assert authenticated.status_code == 200

        client.post("/ui/logout")
        unauthenticated_again = client.get("/api/v1/overview")
        assert unauthenticated_again.status_code == 401
