"""Known-answer tests for the Finance Reporting Pack calculations.

These call the service directly, so they do not depend on how the HTTP route is mounted.
"""
from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook

from app.db import Base, SessionLocal, engine
from app.models import Ingestion
from app.services.finance_dashboard import _number, build_finance_dashboard
from app.services.ingestion import ingest_file

HEADERS = {
    "PNL_ACTUALS": ["PERIOD", "ENTITY", "CURRENCY", "ACCOUNT_CODE", "ACCOUNT_NAME", "STATEMENT_LINE", "CATEGORY", "AMOUNT"],
    "BUDGET": ["PERIOD", "ENTITY", "CURRENCY", "ACCOUNT_CODE", "ACCOUNT_NAME", "STATEMENT_LINE", "CATEGORY", "BUDGET_AMOUNT"],
    "CASH_FLOW": ["PERIOD", "ENTITY", "CURRENCY", "CASH_FLOW_CLASS", "CATEGORY", "AMOUNT"],
    "TRIAL_BALANCE": ["PERIOD", "ENTITY", "CURRENCY", "BALANCE_CLASS", "ACCOUNT_CODE", "ACCOUNT_NAME", "CLOSING_BALANCE"],
}


def _pack(data: dict[str, list[list]]) -> bytes:
    wb = Workbook()
    first = True
    for name, headers in HEADERS.items():
        ws = wb.active if first else wb.create_sheet(name)
        ws.title = name
        first = False
        for line in ("Test pack", "Synthetic", "Header row is row 5", None):
            ws.append([line] if line else [])
        ws.append(headers)
        for row in data.get(name, []):
            ws.append(row)
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


@pytest.fixture(autouse=True)
def _clean_db():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for row in db.query(Ingestion).filter_by(module_key="finance-reporting", tenant_id="demo").all():
            db.delete(row)
        db.commit()
    yield


def _dashboard(data, name="pack.xlsx", **filters):
    with SessionLocal() as db:
        ingest_file(db, module_key="finance-reporting", filename=name, content=_pack(data), header_row=5)
        return build_finance_dashboard(db, **filters)


def _value(body, kpi):
    metric = body["kpis"][kpi]
    return metric["value"] if metric["status"] == "available" else metric["status"]


def _pnl(period, line, amount, entity="E1", currency="USD", category=None):
    return [period, entity, currency, "1", category or line.title(), line, category or line.title(), amount]


FULL_MONTH = [
    ("REVENUE", 1000), ("COGS", 400), ("OPERATING_EXPENSE", 200),
    ("OTHER_INCOME", 0), ("OTHER_EXPENSE", 50), ("TAX", 50),
]


def test_number_parsing():
    assert _number("(250.00)") == -250.0
    assert _number("$1,234.50") == 1234.5
    assert _number("\u20ac300") == 300.0
    assert _number("\u2212 15") == -15.0
    assert _number(12) == 12.0
    assert _number("(-5)") is None
    assert _number("abc") is None
    assert _number("()") is None
    assert _number(True) is None
    assert _number("") is None
    assert _number(None) is None
    assert _number(float("inf")) is None


def test_known_answer_kpis_are_unchanged():
    body = _dashboard({"PNL_ACTUALS": [_pnl("2026-01", line, amt) for line, amt in FULL_MONTH],
                       "CASH_FLOW": [["2026-01", "E1", "USD", "OPERATING", "Ops", 250]]})
    assert _value(body, "revenue") == 1000.0
    assert _value(body, "gross_profit") == 600.0
    assert _value(body, "operating_expenses") == 200.0
    assert _value(body, "net_profit") == 300.0
    assert _value(body, "net_profit_margin") == 30.0
    assert _value(body, "operating_cash_flow") == 250.0
    assert body["warnings"] == []


def test_closing_balances_use_latest_period_not_a_sum():
    tb = [[p, "E1", "USD", "CASH", "1000", "Cash", amt] for p, amt in (("2026-01", 100), ("2026-02", 200), ("2026-03", 300))]
    tb += [["2026-03", "E1", "USD", "ACCOUNTS_RECEIVABLE", "1100", "AR", 40]]
    pnl = [_pnl("2026-01", "REVENUE", 1)]
    body = _dashboard({"PNL_ACTUALS": pnl, "TRIAL_BALANCE": tb})
    balances = {row["label"]: row["value"] for row in body["account_balances"]}
    assert balances == {"Cash": 300.0, "Accounts Receivable": 40.0}

    # The selected range decides which period is "latest".
    with SessionLocal() as db:
        ranged = build_finance_dashboard(db, to_date="2026-02-28")
    assert {row["label"]: row["value"] for row in ranged["account_balances"]} == {"Cash": 200.0}


def test_closing_balances_add_entities_each_at_its_own_latest_period():
    tb = [["2026-03", "A", "USD", "CASH", "1000", "Cash", 300], ["2026-02", "A", "USD", "CASH", "1000", "Cash", 999],
          ["2026-02", "B", "USD", "CASH", "1000", "Cash", 50], ["2026-01", "B", "USD", "CASH", "1000", "Cash", 777]]
    body = _dashboard({"PNL_ACTUALS": [_pnl("2026-01", "REVENUE", 1)], "TRIAL_BALANCE": tb})
    assert body["account_balances"][0]["value"] == 350.0


def test_malformed_period_rows_are_excluded_and_reported():
    pnl = [_pnl("2026-01", "REVENUE", 1000), _pnl("Jan-26", "REVENUE", 500), _pnl("2026/02", "REVENUE", 700)]
    body = _dashboard({"PNL_ACTUALS": pnl})
    assert _value(body, "revenue") == 1000.0
    assert any(w.startswith("2 P&L rows") for w in body["warnings"])


def test_malformed_period_is_reported_for_every_sheet_even_with_a_date_filter():
    data = {"PNL_ACTUALS": [_pnl("2026-01", "REVENUE", 10), _pnl("bad", "REVENUE", 10)],
            "BUDGET": [["bad", "E1", "USD", "1", "x", "REVENUE", "x", 5]],
            "CASH_FLOW": [["bad", "E1", "USD", "OPERATING", "x", 5]],
            "TRIAL_BALANCE": [["bad", "E1", "USD", "CASH", "1", "x", 5]]}
    body = _dashboard(data, from_date="2026-01-01", to_date="2026-01-31")
    text = " ".join(body["warnings"])
    for label in ("P&L rows", "budget rows", "cash-flow rows", "trial-balance rows"):
        assert f"1 {label}" in text, text
    assert body["account_balances"] == []
    # Only the valid actual survives; the malformed budget row contributes nothing.
    assert [(r["category"], r["actual"], r["budget"]) for r in body["budget_vs_actual"]] == [("Revenue", 10.0, None)]


def test_accounting_negatives_and_symbols_are_included():
    pnl = [_pnl("2026-01", "REVENUE", 1000), _pnl("2026-02", "REVENUE", "(250.00)"),
           _pnl("2026-03", "REVENUE", "\u20ac300"), _pnl("2026-04", "REVENUE", "1,234.50")]
    body = _dashboard({"PNL_ACTUALS": pnl})
    assert _value(body, "revenue") == 2284.5
    assert body["warnings"] == []


def test_line_with_no_rows_is_missing_not_zero():
    body = _dashboard({"PNL_ACTUALS": [_pnl("2026-01", "REVENUE", 1000)]})
    assert _value(body, "revenue") == 1000.0
    assert _value(body, "operating_expenses") == "missing_source"

    body = _dashboard({"PNL_ACTUALS": [_pnl("2026-01", "OPERATING_EXPENSE", 200)]}, name="opex-only.xlsx")
    assert _value(body, "revenue") == "missing_source"
    assert _value(body, "operating_expenses") == 200.0


def test_net_profit_still_requires_all_six_lines():
    pnl = [_pnl("2026-01", line, amt) for line, amt in FULL_MONTH if line != "OTHER_INCOME"]
    body = _dashboard({"PNL_ACTUALS": pnl})
    assert _value(body, "gross_profit") == 600.0
    assert _value(body, "net_profit") == "missing_source"


def test_two_currencies_stay_separate():
    pnl = [_pnl("2026-01", "REVENUE", 100, currency="USD"), _pnl("2026-01", "REVENUE", 200, currency="EUR")]
    body = _dashboard({"PNL_ACTUALS": pnl})
    assert body["kpis"]["revenue"]["status"] == "multi_currency"
    assert {x["currency"]: x["value"] for x in body["kpis"]["revenue"]["by_currency"]} == {"EUR": 200.0, "USD": 100.0}


def test_invalid_rows_do_not_leak_into_budget_vs_actual():
    pnl = [_pnl("2026-01", "REVENUE", 1000, category="Product"), ["2026-01", "E1", "", "1", "Product", "REVENUE", "Product", 999]]
    budget = [["2026-01", "E1", "USD", "1", "Product", "REVENUE", "Product", 1100]]
    body = _dashboard({"PNL_ACTUALS": pnl, "BUDGET": budget})
    rows = body["budget_vs_actual"]
    assert [r for r in rows if r["currency"] == ""] == []
    assert {(r["category"], r["actual"], r["budget"]) for r in rows} == {("Product", 1000.0, 1100.0)}
