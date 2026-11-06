from io import BytesIO

from openpyxl import Workbook
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app.models import Ingestion


def _clear_finance_packs():
    with SessionLocal() as db:
        rows = db.query(Ingestion).filter_by(module_key="finance-reporting", tenant_id="demo").all()
        for row in rows:
            db.delete(row)
        db.commit()


def _finance_pack_bytes():
    wb = Workbook()
    ws = wb.active
    ws.title = "PNL_ACTUALS"
    sheets = {
        "PNL_ACTUALS": ["PERIOD", "ENTITY", "CURRENCY", "ACCOUNT_CODE", "ACCOUNT_NAME", "STATEMENT_LINE", "CATEGORY", "AMOUNT"],
        "BUDGET": ["PERIOD", "ENTITY", "CURRENCY", "ACCOUNT_CODE", "ACCOUNT_NAME", "STATEMENT_LINE", "CATEGORY", "BUDGET_AMOUNT"],
        "CASH_FLOW": ["PERIOD", "ENTITY", "CURRENCY", "CASH_FLOW_CLASS", "CATEGORY", "AMOUNT"],
        "TRIAL_BALANCE": ["PERIOD", "ENTITY", "CURRENCY", "BALANCE_CLASS", "ACCOUNT_CODE", "ACCOUNT_NAME", "CLOSING_BALANCE"],
    }
    for name, headers in sheets.items():
        sh = ws if name == "PNL_ACTUALS" else wb.create_sheet(name)
        sh.append([f"Finance reporting template — {name}"])
        sh.append(["Test dataset; not a production company record."])
        sh.append(["Header row is row 5."])
        sh.append([])
        sh.append(headers)
    pnl = wb["PNL_ACTUALS"]
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "4000", "Product Sales", "REVENUE", "Product sales", 1000])
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "5000", "Cost of Sales", "COGS", "Materials", 400])
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "6100", "Operating Expense", "OPERATING_EXPENSE", "Payroll", 200])
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "7100", "Other Expense", "OTHER_EXPENSE", "Interest", 50])
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "7200", "Other Income", "OTHER_INCOME", "Other income", 0])
    pnl.append(["2026-01", "Plant 100 — SFO", "USD", "8100", "Tax", "TAX", "Income tax", 50])
    budget = wb["BUDGET"]
    budget.append(["2026-01", "Plant 100 — SFO", "USD", "4000", "Product Sales", "REVENUE", "Product sales", 1100])
    budget.append(["2026-01", "Plant 100 — SFO", "USD", "5000", "Cost of Sales", "COGS", "Materials", 450])
    budget.append(["2026-01", "Plant 100 — SFO", "USD", "6100", "Operating Expense", "OPERATING_EXPENSE", "Payroll", 250])
    cash = wb["CASH_FLOW"]
    cash.append(["2026-01", "Plant 100 — SFO", "USD", "OPERATING", "Operating activities", 250])
    cash.append(["2026-01", "Plant 100 — SFO", "USD", "INVESTING", "Equipment", -40])
    cash.append(["2026-01", "Plant 100 — SFO", "USD", "FINANCING", "Loan proceeds", 100])
    tb = wb["TRIAL_BALANCE"]
    tb.append(["2026-01", "Plant 100 — SFO", "USD", "CASH", "1000", "Cash", 500])
    tb.append(["2026-01", "Plant 100 — SFO", "USD", "ACCOUNTS_RECEIVABLE", "1100", "Accounts Receivable", 200])
    tb.append(["2026-01", "Plant 100 — SFO", "USD", "ACCOUNTS_PAYABLE", "2000", "Accounts Payable", 150])
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def test_finance_dashboard_missing_pack_is_explicit():
    _clear_finance_packs()
    with TestClient(app) as client:
        response = client.get("/api/v1/finance/dashboard")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "missing_source"
        assert body["kpis"]["revenue"]["status"] == "missing_source"
        assert "Finance Reporting Pack" in body["message"]


def test_finance_dashboard_calculates_only_from_uploaded_normalized_pack():
    _clear_finance_packs()
    content = _finance_pack_bytes()
    with TestClient(app) as client:
        upload = client.post(
            "/api/v1/ingestions",
            data={"module_key": "finance-reporting", "header_row": "5"},
            files={"file": ("finance-pack-test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert upload.status_code == 200, upload.text
        response = client.get("/api/v1/finance/dashboard", params={
            "from_date": "2026-01-01", "to_date": "2026-01-31", "entity": "Plant 100 — SFO", "currency": "USD"
        })
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "available"
        assert body["kpis"]["revenue"]["value"] == 1000.0
        assert body["kpis"]["gross_profit"]["value"] == 600.0
        assert body["kpis"]["operating_expenses"]["value"] == 200.0
        assert body["kpis"]["net_profit"]["value"] == 300.0
        assert body["kpis"]["net_profit_margin"]["value"] == 30.0
        assert body["kpis"]["operating_cash_flow"]["value"] == 250.0
        assert body["revenue_trend"][0]["budget"] == 1100.0
        assert {x["label"] for x in body["account_balances"]} == {"Cash", "Accounts Receivable", "Accounts Payable"}


def test_finance_dashboard_entity_filter_excludes_other_entities():
    _clear_finance_packs()
    content = _finance_pack_bytes()
    with TestClient(app) as client:
        client.post(
            "/api/v1/ingestions",
            data={"module_key": "finance-reporting", "header_row": "5"},
            files={"file": ("finance-pack-filter-test.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        response = client.get("/api/v1/finance/dashboard", params={"entity": "Plant 200 — Austin", "currency": "USD"})
        assert response.status_code == 200, response.text
        assert response.json()["kpis"]["revenue"]["status"] == "missing_source"
