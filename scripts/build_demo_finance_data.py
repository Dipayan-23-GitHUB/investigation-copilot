"""Build a clearly-labelled synthetic finance dashboard dataset from bundled sample extracts.

The Source Ledger workbooks contain fictional, illustrative values. Account labels below
are demo-only assumptions and must never be treated as a customer chart of accounts.
"""
from __future__ import annotations
import json
from calendar import month_abbr, monthrange
from datetime import date
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "sample_data"
OUTPUT = ROOT / "app" / "data" / "demo_finance.json"


def sheet_records(filename: str, sheet_name: str) -> list[dict]:
    wb = load_workbook(SAMPLES / filename, read_only=True, data_only=True)
    try:
        ws = next(w for w in wb.worksheets if w.title.upper().startswith(sheet_name.upper()))
        all_rows = list(ws.iter_rows(values_only=True))
        # Source Ledger's header row is row 5: four leading rows precede column names.
        headers = [str(v).strip() if v is not None else "" for v in all_rows[4]]
        result = []
        for row in all_rows[5:]:
            if not row or all(v is None for v in row):
                continue
            item = {headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]}
            if item and str(item.get(headers[0], "")).lower() != "total":
                result.append(item)
        return result
    finally:
        wb.close()


def num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build() -> dict:
    gl = sheet_records("02-corporate-controller-sample-extract.xlsx", "BSEG")
    coep = sheet_records("05-fpa-sample-extract.xlsx", "COEP")
    cash = sheet_records("06-treasury-sample-extract.xlsx", "CE_STATEMENT_LINES")

    # These three account roles are explicit synthetic demo assumptions. The sample file
    # includes account IDs and amounts but no Chart of Accounts text/meaning.
    sales_anchor = sum(num(r.get("DMBTR")) for r in gl if str(r.get("HKONT")) == "500000" and r.get("SHKZG") == "H")
    cogs_anchor = sum(num(r.get("DMBTR")) for r in gl if str(r.get("HKONT")) == "600000" and r.get("SHKZG") == "S")
    opex_anchor = sum(num(r.get("DMBTR")) for r in gl if str(r.get("HKONT")) == "700000" and r.get("SHKZG") == "S")
    if not sales_anchor or not cogs_anchor or not opex_anchor:
        raise ValueError("Expected demo GL anchor rows were not found in the bundled corporate-controller workbook.")

    coep_jul_actual = sum(num(r.get("WTGBTR")) for r in coep if str(r.get("GJAHR")) == "2025" and str(r.get("PERIO")) == "007" and str(r.get("WRTTP")) == "04")
    coep_jul_plan = sum(num(r.get("WTGBTR")) for r in coep if str(r.get("GJAHR")) == "2025" and str(r.get("PERIO")) == "007" and str(r.get("WRTTP")) == "01")
    # Use only reconciled USD bank lines as a scale/provenance check. This is not a formal
    # cash-flow classification; monthly cash-flow rows below are synthetic projections.
    reconciled_usd_cash_net = sum(num(r.get("AMOUNT")) for r in cash if r.get("TRX_CURR_CODE") == "USD" and r.get("RECON_STATUS") == "RECONCILED")

    multipliers = [1.00, 1.03, 1.01, 1.07, 1.10, 1.12, 1.08, 1.13, 1.16, 1.19, 1.17, 1.22]
    budget_factors = [1.02, 1.01, 1.00, 1.02, 1.03, 1.01, 1.02, 1.00, 1.01, 1.02, 1.00, 1.01]
    months = []
    start_year, start_month = 2025, 7
    for idx, multiplier in enumerate(multipliers):
        month_num = ((start_month - 1 + idx) % 12) + 1
        year = start_year + ((start_month - 1 + idx) // 12)
        period = f"{year:04d}-{month_num:02d}"
        revenue = round(sales_anchor * multiplier, 2)
        cogs_ratio = cogs_anchor / sales_anchor
        cogs = round(revenue * cogs_ratio * (1 - 0.0015 * idx), 2)
        gross_profit = round(revenue - cogs, 2)
        opex = round(opex_anchor * multiplier * (1 + 0.001 * idx), 2)
        other = round(revenue * 0.025, 2)
        pretax = gross_profit - opex - other
        tax = round(max(pretax, 0) * 0.21, 2)
        net_profit = round(pretax - tax, 2)
        budget_revenue = round(revenue * budget_factors[idx], 2)
        budget_cogs = round(budget_revenue * cogs_ratio * 1.01, 2)
        budget_opex = round(opex * 1.025, 2)
        budget_net = round(budget_revenue - budget_cogs - budget_opex - budget_revenue * 0.025 - max(budget_revenue - budget_cogs - budget_opex - budget_revenue * 0.025, 0) * 0.21, 2)
        da = round(revenue * 0.035, 2)
        wc_change = round(revenue * (0.018 + (idx % 3) * 0.002), 2)
        operating_cf = round(net_profit + da - wc_change, 2)
        investing_cf = round(-revenue * (0.032 + (idx % 2) * 0.004), 2)
        financing_cf = round(revenue * (0.006 if idx % 3 == 0 else -0.004), 2)
        net_cf = round(operating_cf + investing_cf + financing_cf, 2)
        months.append({
            "period": period, "period_label": f"{month_abbr[month_num]} {str(year)[-2:]}",
            "entity": "Plant 100 — SFO", "currency": "USD",
            "revenue": revenue, "budget_revenue": budget_revenue,
            "cogs": cogs, "budget_cogs": budget_cogs,
            "gross_profit": gross_profit, "opex": opex, "budget_opex": budget_opex,
            "other_expenses": other, "tax": tax, "net_profit": net_profit,
            "budget_net_profit": budget_net,
            "operating_cash_flow": operating_cf, "investing_cash_flow": investing_cf,
            "financing_cash_flow": financing_cf, "net_cash_flow": net_cf,
            "revenue_categories": {
                "Product sales": round(revenue * 0.74, 2),
                "Service income": round(revenue * 0.14, 2),
                "Spare parts": round(revenue * 0.08, 2),
                "Other income": round(revenue - round(revenue * 0.74, 2) - round(revenue * 0.14, 2) - round(revenue * 0.08, 2), 2),
            },
            "expense_categories": {
                "Salaries & benefits": round(opex * 0.34, 2),
                "Marketing": round(opex * 0.13, 2),
                "Rent & utilities": round(opex * 0.16, 2),
                "Software & tools": round(opex * 0.07, 2),
                "Logistics": round(opex * 0.18, 2),
                "Other expenses": round(opex - sum(round(opex * x, 2) for x in (0.34,0.13,0.16,0.07,0.18)), 2),
            },
        })

    first = months[0]
    last = months[-1]
    # Illustrative balances; they are not drawn from a trial balance in the sample pack.
    accounts = [
        {"name": "Cash & bank", "amount": 285000.0, "type": "asset"},
        {"name": "Accounts receivable", "amount": 194000.0, "type": "asset"},
        {"name": "Inventory", "amount": 318000.0, "type": "asset"},
        {"name": "Property, plant & equipment", "amount": 465000.0, "type": "asset"},
        {"name": "Accounts payable", "amount": 172000.0, "type": "liability"},
        {"name": "Term debt", "amount": 260000.0, "type": "liability"},
        {"name": "Share capital & retained earnings", "amount": 830000.0, "type": "equity"},
    ]
    forecast = []
    recent_growth = (months[-1]["revenue"] / months[-4]["revenue"]) ** (1/3) - 1
    for offset in range(1, 4):
        month_num = last["period"].split("-")[1]
        y, m = map(int, last["period"].split("-"))
        next_m = m + offset
        fy = y + (next_m - 1) // 12
        fm = ((next_m - 1) % 12) + 1
        rev = round(last["revenue"] * ((1 + recent_growth) ** offset), 2)
        cogs = round(rev * (last["cogs"] / last["revenue"]), 2)
        gp = round(rev - cogs, 2)
        op = round(last["opex"] * (rev / last["revenue"]), 2)
        np = round((gp - op - rev * 0.025) * 0.79, 2)
        forecast.append({"period": f"{fy:04d}-{fm:02d}", "period_label": f"{month_abbr[fm]} {str(fy)[-2:]}", "revenue": rev, "gross_profit": gp, "net_profit": np, "type": "Forecast"})

    return {
        "data_mode": "DEMO_SYNTHETIC",
        "company": "Meridian Bicycle Co. (fictional sample company)",
        "entity": "Plant 100 — SFO",
        "currency": "USD",
        "period_start": months[0]["period"] + "-01",
        "period_end": date(*map(int, months[-1]["period"].split("-")), 1).replace(day=monthrange(*map(int, months[-1]["period"].split("-")))[1]).isoformat(),
        "periods": months,
        "forecast": forecast,
        "accounts": accounts,
        "provenance": {
            "source_files": [
                "sample_data/02-corporate-controller-sample-extract.xlsx (BKPF/BSEG)",
                "sample_data/05-fpa-sample-extract.xlsx (COEP)",
                "sample_data/06-treasury-sample-extract.xlsx (CE_STATEMENT_HEADERS/CE_STATEMENT_LINES)",
            ],
            "anchors": {
                "BSEG account 500000 credit-side amount used only as a scale anchor": round(sales_anchor, 2),
                "BSEG account 600000 debit-side amount used only as a scale anchor": round(cogs_anchor, 2),
                "BSEG account 700000 debit-side amount used only as a scale anchor": round(opex_anchor, 2),
                "COEP July 2025 actual cost-element lines (amount; not consolidated to P&L)": round(coep_jul_actual, 2),
                "COEP July 2025 plan cost-element lines (amount; not consolidated to P&L)": round(coep_jul_plan, 2),
                "Treasury reconciled USD statement lines net movement (not a classified cash flow)": round(reconciled_usd_cash_net, 2),
            },
            "account_mapping": {
                "500000": "Synthetic demo revenue assumption",
                "600000": "Synthetic demo cost-of-sales assumption",
                "700000": "Synthetic demo operating-expense assumption",
            },
            "assumptions": [
                "The bundled Source Ledger workbooks are fictional illustrative examples, not customer records.",
                "The sample GL workbook provides account IDs and amounts but no Chart of Accounts descriptions. Account-role mappings are illustrative assumptions used only to size this synthetic dataset.",
                "Only the first-month anchors are tied to sample row magnitudes. Remaining monthly values, categories, budgets, forecasts and balance-sheet summaries are deterministic synthetic demo values.",
                "The demo P&L, cash flow and account balances are not reconciled financial statements and must not be used for management reporting, audit, credit, tax or external disclosure.",
            ],
        },
    }


if __name__ == "__main__":
    payload = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(payload['periods'])} demo periods. DATA_MODE={payload['data_mode']}")
