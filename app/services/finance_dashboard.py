from __future__ import annotations

from collections import defaultdict
from datetime import date
import math
from typing import Any

from sqlalchemy.orm import Session, joinedload

from ..models import Ingestion, SourceSheet


PNL_LINES = {"REVENUE", "COGS", "OPERATING_EXPENSE", "OTHER_INCOME", "OTHER_EXPENSE", "TAX"}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("$", "").strip()
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _period(value: Any) -> str:
    raw = _text(value)
    if len(raw) >= 7 and raw[4] == "-":
        candidate = raw[:7]
        try:
            date.fromisoformat(candidate + "-01")
            return candidate
        except ValueError:
            return ""
    return ""


def _matches(row: dict, from_period: str, to_period: str, entity: str, currency: str) -> bool:
    period = _period(row.get("PERIOD"))
    if not period:
        return False
    if from_period and period < from_period:
        return False
    if to_period and period > to_period:
        return False
    row_entity = _text(row.get("ENTITY"))
    if entity and entity.casefold() not in {"all entities", "all"} and row_entity.casefold() != entity.casefold():
        return False
    row_currency = _text(row.get("CURRENCY")).upper()
    if currency and row_currency != currency.upper():
        return False
    return True


def _metric(values: dict[str, float], empty_message: str, percent: bool = False) -> dict:
    cleaned = {k: round(v, 2) for k, v in sorted(values.items()) if abs(v) > 1e-9 or v == 0}
    if not cleaned:
        return {"status": "missing_source", "value": None, "message": empty_message}
    if len(cleaned) == 1:
        curr, value = next(iter(cleaned.items()))
        return {"status": "available", "value": value, "currency": curr, "message": "Derived from uploaded finance reporting rows."}
    return {"status": "multi_currency", "value": None, "by_currency": [{"currency": k, "value": v} for k, v in cleaned.items()],
            "message": "Multiple currencies are kept separate; no FX conversion is applied."}


def _load_pack(db: Session) -> tuple[dict[str, list[dict]], list[dict], int]:
    sheets: dict[str, list[dict]] = defaultdict(list)
    ingestion_meta: list[dict] = []
    row_total = 0
    latest = (db.query(Ingestion)
              .filter(Ingestion.module_key == "finance-reporting", Ingestion.tenant_id == "demo")
              .order_by(Ingestion.created_at.desc())
              .first())
    if latest is None:
        return sheets, ingestion_meta, row_total
    query = (
        db.query(SourceSheet)
        .join(Ingestion, SourceSheet.ingestion_id == Ingestion.id)
        .options(joinedload(SourceSheet.rows), joinedload(SourceSheet.ingestion))
        .filter(Ingestion.id == latest.id)
        .order_by(SourceSheet.sheet_name.asc())
    )
    for sheet in query.all():
        key = sheet.sheet_name.strip().upper()
        rows = [r.data or {} for r in sorted(sheet.rows, key=lambda item: item.row_number)]
        sheets[key].extend(rows)
        row_total += len(rows)
        if sheet.ingestion:
            ingestion_meta.append({"id": sheet.ingestion.id, "filename": sheet.ingestion.filename,
                                    "module_key": sheet.ingestion.module_key, "created_at": sheet.ingestion.created_at.isoformat() if sheet.ingestion.created_at else None})
    # One metadata record per ingestion, not one per sheet.
    unique = {x["id"]: x for x in ingestion_meta}
    return sheets, list(unique.values()), row_total


def build_finance_dashboard(
    db: Session,
    *,
    from_date: str | None = None,
    to_date: str | None = None,
    entity: str | None = None,
    currency: str | None = None,
) -> dict:
    sheets, ingestions, row_total = _load_pack(db)
    from_period = _period(from_date) if from_date else ""
    to_period = _period(to_date) if to_date else ""
    entity_filter = _text(entity)
    currency_filter = _text(currency).upper()

    if not ingestions:
        missing = ["PNL_ACTUALS", "BUDGET", "CASH_FLOW", "TRIAL_BALANCE"]
        msg = ("No Finance Reporting Pack has been uploaded yet. Upload the normalized finance workbook; "
               "the 12 Source Ledger workbooks are source extracts and are not, by themselves, a reconciled management P&L.")
        empty = {k: {"status": "missing_source", "value": None, "message": msg} for k in
                 ["revenue", "gross_profit", "net_profit", "operating_expenses", "operating_cash_flow", "net_profit_margin"]}
        return {"status": "missing_source", "message": msg, "ingestion_count": 0, "row_count": 0,
                "sheets_present": [], "sheets_missing": missing, "currencies": [], "entities": [], "kpis": empty,
                "revenue_trend": [], "profitability_trend": [], "revenue_by_category": [], "expenses_by_category": [],
                "cash_flow_by_period": [], "budget_vs_actual": [], "account_balances": [], "profitability_summary": []}

    required = ["PNL_ACTUALS", "BUDGET", "CASH_FLOW", "TRIAL_BALANCE"]
    missing = [name for name in required if name not in sheets]
    all_rows = [row for name in required for row in sheets.get(name, [])]
    currencies = sorted({_text(r.get("CURRENCY")).upper() for r in all_rows if _text(r.get("CURRENCY"))})
    entities = sorted({_text(r.get("ENTITY")) for r in all_rows if _text(r.get("ENTITY"))})

    pnl = [r for r in sheets.get("PNL_ACTUALS", []) if _matches(r, from_period, to_period, entity_filter, currency_filter)]
    budget = [r for r in sheets.get("BUDGET", []) if _matches(r, from_period, to_period, entity_filter, currency_filter)]
    cash = [r for r in sheets.get("CASH_FLOW", []) if _matches(r, from_period, to_period, entity_filter, currency_filter)]
    tb = [r for r in sheets.get("TRIAL_BALANCE", []) if _matches(r, from_period, to_period, entity_filter, currency_filter)]

    pnl_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    revenue_category: dict[tuple[str, str], float] = defaultdict(float)
    expense_category: dict[tuple[str, str], float] = defaultdict(float)
    period_totals: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    invalid_pnl_rows = 0
    for row in pnl:
        line = _text(row.get("STATEMENT_LINE")).upper().replace(" ", "_")
        curr = _text(row.get("CURRENCY")).upper()
        amount = _number(row.get("AMOUNT"))
        period = _period(row.get("PERIOD"))
        if line not in PNL_LINES or not curr or amount is None or not period:
            invalid_pnl_rows += 1
            continue
        pnl_totals[curr][line] += amount
        period_totals[(period, curr)][line] += amount
        category = _text(row.get("CATEGORY")) or _text(row.get("ACCOUNT_NAME")) or _text(row.get("ACCOUNT_CODE")) or "Uncategorized"
        if line == "REVENUE":
            revenue_category[(category, curr)] += amount
        elif line in {"COGS", "OPERATING_EXPENSE", "OTHER_EXPENSE", "TAX"}:
            expense_category[(category, curr)] += amount

    currencies_with_pnl = sorted(pnl_totals)
    revenue_values: dict[str, float] = {}
    gross_values: dict[str, float] = {}
    net_values: dict[str, float] = {}
    opex_values: dict[str, float] = {}
    margin_values: dict[str, float] = {}
    profitability_summary = []
    for curr, vals in pnl_totals.items():
        revenue = vals.get("REVENUE", 0.0)
        cogs = vals.get("COGS", 0.0)
        opex = vals.get("OPERATING_EXPENSE", 0.0)
        other_income = vals.get("OTHER_INCOME", 0.0)
        other_expense = vals.get("OTHER_EXPENSE", 0.0)
        tax = vals.get("TAX", 0.0)
        revenue_values[curr] = revenue
        opex_values[curr] = opex
        gross = revenue - cogs if {"REVENUE", "COGS"}.issubset(vals.keys()) else None
        operating = gross - opex if gross is not None and "OPERATING_EXPENSE" in vals else None
        complete_pnl = PNL_LINES.issubset(vals.keys())
        net = operating + other_income - other_expense - tax if operating is not None and complete_pnl else None
        if gross is not None:
            gross_values[curr] = gross
        if net is not None:
            net_values[curr] = net
            if abs(revenue) > 1e-9:
                margin_values[curr] = net / revenue * 100.0
        profitability_summary.append({"currency": curr, "revenue": round(revenue, 2), "gross_profit": round(gross, 2) if gross is not None else None,
                                      "operating_profit": round(operating, 2) if operating is not None else None,
                                      "net_profit": round(net, 2) if net is not None else None,
                                      "gross_margin_pct": round(gross / revenue * 100, 2) if gross is not None and abs(revenue) > 1e-9 else None,
                                      "net_margin_pct": round(net / revenue * 100, 2) if net is not None and abs(revenue) > 1e-9 else None})

    cash_by_currency: dict[str, float] = defaultdict(float)
    cash_period: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    invalid_cash_rows = 0
    for row in cash:
        cls = _text(row.get("CASH_FLOW_CLASS")).upper()
        curr = _text(row.get("CURRENCY")).upper()
        amount = _number(row.get("AMOUNT"))
        period = _period(row.get("PERIOD"))
        if cls not in {"OPERATING", "INVESTING", "FINANCING"} or not curr or amount is None or not period:
            invalid_cash_rows += 1
            continue
        cash_period[(period, curr)][cls] += amount
        if cls == "OPERATING":
            cash_by_currency[curr] += amount

    budget_period: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    invalid_budget_rows = 0
    for row in budget:
        line = _text(row.get("STATEMENT_LINE")).upper().replace(" ", "_")
        curr = _text(row.get("CURRENCY")).upper()
        amount = _number(row.get("BUDGET_AMOUNT"))
        period = _period(row.get("PERIOD"))
        if line not in PNL_LINES or not curr or amount is None or not period:
            invalid_budget_rows += 1
            continue
        category = _text(row.get("CATEGORY")) or _text(row.get("ACCOUNT_NAME")) or _text(row.get("ACCOUNT_CODE")) or line.replace("_", " ").title()
        budget_period[(period, curr, category)]["budget"] += amount

    actual_by_period_category: dict[tuple[str, str, str], float] = defaultdict(float)
    for row in pnl:
        line = _text(row.get("STATEMENT_LINE")).upper().replace(" ", "_")
        if line not in PNL_LINES:
            continue
        amount = _number(row.get("AMOUNT"))
        if amount is None:
            continue
        curr = _text(row.get("CURRENCY")).upper()
        period = _period(row.get("PERIOD"))
        category = _text(row.get("CATEGORY")) or _text(row.get("ACCOUNT_NAME")) or _text(row.get("ACCOUNT_CODE")) or line.replace("_", " ").title()
        actual_by_period_category[(period, curr, category)] += amount
    for key, actual in actual_by_period_category.items():
        budget_period[key]["actual"] += actual

    balance_totals: dict[tuple[str, str], float] = defaultdict(float)
    invalid_tb_rows = 0
    for row in tb:
        cls = _text(row.get("BALANCE_CLASS")).upper().replace(" ", "_")
        curr = _text(row.get("CURRENCY")).upper()
        value = _number(row.get("CLOSING_BALANCE"))
        if cls not in {"CASH", "ACCOUNTS_RECEIVABLE", "ACCOUNTS_PAYABLE", "INVENTORY", "OTHER"} or not curr or value is None:
            invalid_tb_rows += 1
            continue
        label = {"ACCOUNTS_RECEIVABLE": "Accounts Receivable", "ACCOUNTS_PAYABLE": "Accounts Payable"}.get(cls, cls.title())
        balance_totals[(label, curr)] += value

    def rows_by_category(source: dict[tuple[str, str], float]) -> list[dict]:
        return [{"label": label, "currency": curr, "value": round(value, 2)}
                for (label, curr), value in sorted(source.items(), key=lambda item: abs(item[1]), reverse=True)]

    revenue_budget_period: dict[tuple[str, str], float] = defaultdict(float)
    for row in budget:
        line = _text(row.get("STATEMENT_LINE")).upper().replace(" ", "_")
        if line == "REVENUE":
            amount = _number(row.get("BUDGET_AMOUNT"))
            period = _period(row.get("PERIOD"))
            curr = _text(row.get("CURRENCY")).upper()
            if amount is not None and period and curr:
                revenue_budget_period[(period, curr)] += amount

    revenue_trend = []
    profitability_trend = []
    for (period, curr), values in sorted(period_totals.items()):
        revenue = values.get("REVENUE", 0.0)
        gross = revenue - values.get("COGS", 0.0)
        operating = gross - values.get("OPERATING_EXPENSE", 0.0)
        net = operating + values.get("OTHER_INCOME", 0.0) - values.get("OTHER_EXPENSE", 0.0) - values.get("TAX", 0.0)
        revenue_trend.append({"period": period, "currency": curr, "actual": round(revenue, 2),
                              "budget": round(revenue_budget_period[(period, curr)], 2) if (period, curr) in revenue_budget_period else None})
        complete_period = PNL_LINES.issubset(values.keys())
        gross_complete = {"REVENUE", "COGS"}.issubset(values.keys())
        profitability_trend.append({"period": period, "currency": curr,
                                    "gross_profit": round(gross, 2) if gross_complete else None,
                                    "net_profit": round(net, 2) if complete_period else None,
                                    "net_margin_pct": round(net / revenue * 100, 2) if complete_period and abs(revenue) > 1e-9 else None})
    budget_vs_actual = []
    for (period, curr, category), values in sorted(budget_period.items()):
        budget_vs_actual.append({"period": period, "currency": curr, "category": category,
                                 "actual": round(values["actual"], 2) if "actual" in values else None,
                                 "budget": round(values["budget"], 2) if "budget" in values else None})

    warnings = []
    if missing:
        warnings.append("Missing sheets: " + ", ".join(missing))
    if invalid_pnl_rows:
        warnings.append(f"{invalid_pnl_rows} P&L rows did not meet the required field/value rules and were excluded.")
    if invalid_budget_rows:
        warnings.append(f"{invalid_budget_rows} budget rows did not meet the required field/value rules and were excluded.")
    if invalid_cash_rows:
        warnings.append(f"{invalid_cash_rows} cash-flow rows did not meet the required field/value rules and were excluded.")
    if invalid_tb_rows:
        warnings.append(f"{invalid_tb_rows} trial-balance rows did not meet the required field/value rules and were excluded.")
    if len(currencies) > 1 and not currency_filter:
        warnings.append("Multiple currencies are present. KPI totals are returned per currency; charts should be filtered to one currency for meaningful scale comparison.")

    return {
        "status": "available" if pnl_totals else "incomplete",
        "message": "Finance reporting rows loaded. Figures are calculated from the normalized upload pack; no FX conversion is applied." if pnl_totals else "Finance reporting pack uploaded, but no valid P&L actual rows were found for the selected filters.",
        "ingestion_count": len(ingestions), "row_count": row_total,
        "files": ingestions,
        "sheets_present": sorted(sheets), "sheets_missing": missing,
        "currencies": currencies, "entities": entities, "selected_currency": currency_filter or None,
        "selected_entity": entity_filter or "All Entities", "from_period": from_period or None, "to_period": to_period or None,
        "warnings": warnings,
        "kpis": {
            "revenue": _metric(revenue_values, "Upload P&L actual rows with STATEMENT_LINE=REVENUE."),
            "gross_profit": _metric(gross_values, "Gross profit requires both REVENUE and COGS rows for the selected currency and period."),
            "net_profit": _metric(net_values, "Net profit requires rows for all six P&L lines: REVENUE, COGS, OPERATING_EXPENSE, OTHER_INCOME, OTHER_EXPENSE and TAX."),
            "operating_expenses": _metric(opex_values, "Upload P&L actual rows classified as OPERATING_EXPENSE."),
            "operating_cash_flow": _metric(dict(cash_by_currency), "Upload cash-flow rows classified as OPERATING; positive inflows and negative outflows."),
            "net_profit_margin": _metric(margin_values, "Net profit margin requires a complete P&L and non-zero revenue in the selected period." , percent=True),
        },
        "revenue_trend": revenue_trend,
        "profitability_trend": profitability_trend,
        "revenue_by_category": rows_by_category(revenue_category),
        "expenses_by_category": rows_by_category(expense_category),
        "cash_flow_by_period": [{"period": period, "currency": curr,
                                 "operating": round(values["OPERATING"], 2) if "OPERATING" in values else None,
                                 "investing": round(values["INVESTING"], 2) if "INVESTING" in values else None,
                                 "financing": round(values["FINANCING"], 2) if "FINANCING" in values else None}
                                for (period, curr), values in sorted(cash_period.items())],
        "budget_vs_actual": budget_vs_actual,
        "account_balances": rows_by_category(balance_totals),
        "profitability_summary": profitability_summary,
    }
