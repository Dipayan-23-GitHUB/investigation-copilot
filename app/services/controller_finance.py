from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from calendar import monthrange
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..models import ActionRecord, ExceptionRecord

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "demo_finance.json"


def _load_demo() -> dict[str, Any]:
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sum(rows: list[dict], key: str) -> float:
    return round(sum(float(row.get(key) or 0) for row in rows), 2)


def _aggregate_categories(rows: list[dict], field: str) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        for label, value in (row.get(field) or {}).items():
            totals[str(label)] += float(value or 0)
    grand_total = sum(totals.values())
    return [
        {"name": name, "value": round(value, 2), "share": round(value / grand_total * 100, 2) if grand_total else 0}
        for name, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def build_controller_dashboard(
    db: Session,
    from_date: str | None = None,
    to_date: str | None = None,
    entity: str | None = None,
) -> dict[str, Any]:
    """Return a fully-populated, explicitly synthetic demo finance dashboard.

    Finance amounts come from a reproducible fixture generated from the repository's
    fictional Source Ledger extracts. Exception and action counts are read from the
    current database so the operational register remains live.
    """
    base = _load_demo()
    try:
        start = date.fromisoformat(from_date) if from_date else date.fromisoformat(base["period_start"])
        end = date.fromisoformat(to_date) if to_date else date.fromisoformat(base["period_end"])
    except ValueError as exc:
        raise ValueError("Date filters must use YYYY-MM-DD format.") from exc
    if start > end:
        raise ValueError("From date must be earlier than or equal to To date.")

    normalized_entity = (entity or "All Entities").strip().lower()
    known_entities = {row["entity"].lower() for row in base["periods"]}
    if normalized_entity not in {"all", "all entities", *known_entities}:
        raise ValueError(f"No demo finance data is available for entity '{entity}'.")
    periods = []
    for row in base["periods"]:
        year, month = map(int, row["period"].split("-"))
        month_start = date(year, month, 1)
        month_end = date(year, month, monthrange(year, month)[1])
        overlaps_selected_window = month_end >= start and month_start <= end
        entity_matches = normalized_entity in {"all", "all entities", row["entity"].lower()}
        if overlaps_selected_window and entity_matches:
            periods.append(row)
    if not periods:
        available = f"{base['periods'][0]['period']} through {base['periods'][-1]['period']}"
        raise ValueError(f"No demo finance months match the selected date/entity filter. Available sample period: {available}.")
    selected_period_note = "Monthly data: a month is included when it overlaps the selected dates; monthly values are not prorated by day."

    revenue = _sum(periods, "revenue")
    cogs = _sum(periods, "cogs")
    gross_profit = round(revenue - cogs, 2)
    opex = _sum(periods, "opex")
    other = _sum(periods, "other_expenses")
    tax = _sum(periods, "tax")
    net_profit = _sum(periods, "net_profit")
    budget_revenue = _sum(periods, "budget_revenue")
    budget_cogs = _sum(periods, "budget_cogs")
    budget_opex = _sum(periods, "budget_opex")
    budget_net_profit = _sum(periods, "budget_net_profit")
    ocf = _sum(periods, "operating_cash_flow")
    icf = _sum(periods, "investing_cash_flow")
    fcf = _sum(periods, "financing_cash_flow")
    ncf = _sum(periods, "net_cash_flow")

    exceptions = db.query(ExceptionRecord).order_by(ExceptionRecord.impact_amount.desc()).all()
    actions = db.query(ActionRecord).all()
    active_exceptions = [row for row in exceptions if str(row.status).lower() not in {"closed", "resolved", "completed", "cancelled"}]
    alerts = []
    for row in active_exceptions[:12]:
        alerts.append({
            "id": row.id,
            "title": row.title,
            "material_id": row.material_id,
            "impact_amount": round(float(row.impact_amount or 0), 2),
            "currency": row.currency or "USD",
            "priority": row.priority,
            "status": row.status,
            "root_cause_found": bool(row.root_cause_found),
            "demo_only": bool((row.investigation or {}).get("demo_only", False)),
        })

    period_label = f"{periods[0]['period_label']} – {periods[-1]['period_label']}"
    last_year, last_month = map(int, periods[-1]["period"].split("-"))
    period_end = date(last_year, last_month, monthrange(last_year, last_month)[1]).isoformat()
    return {
        "data_mode": base["data_mode"],
        "company": base["company"],
        "entity": entity or base["entity"],
        "currency": base["currency"],
        "period_label": period_label,
        "period_start": periods[0]["period"] + "-01",
        "period_end": period_end,
        "selected_period_note": selected_period_note,
        "data_notice": (
            "DEMO DATA — synthetic finance values generated from the repository's fictional Meridian sample extracts. "
            "These are not customer actuals, not a reconciled P&L, not a trial balance and not suitable for statutory, "
            "audit, tax, credit or external reporting. Replace with mapped customer extracts before operational use."
        ),
        "kpis": {
            "revenue": revenue,
            "gross_profit": gross_profit,
            "net_profit": net_profit,
            "operating_expenses": opex,
            "operating_cash_flow": ocf,
            "net_profit_margin": round(net_profit / revenue * 100, 2) if revenue else 0,
            "revenue_vs_budget_pct": round((revenue - budget_revenue) / budget_revenue * 100, 2) if budget_revenue else 0,
            "gross_margin_pct": round(gross_profit / revenue * 100, 2) if revenue else 0,
            "open_exception_count": len(active_exceptions),
            "unresolved_exception_count": sum(1 for row in active_exceptions if not row.root_cause_found),
            "open_action_count": sum(1 for row in actions if str(row.status).lower() not in {"completed", "closed", "cancelled"}),
        },
        "revenue_trend": [
            {"period": row["period"], "label": row["period_label"], "actual": row["revenue"], "budget": row["budget_revenue"]}
            for row in periods
        ],
        "profit_trend": [
            {"period": row["period"], "label": row["period_label"], "gross_profit": row["gross_profit"],
             "net_profit": row["net_profit"], "margin_pct": round(row["net_profit"] / row["revenue"] * 100, 2) if row["revenue"] else 0}
            for row in periods
        ],
        "revenue_categories": _aggregate_categories(periods, "revenue_categories"),
        "expense_categories": _aggregate_categories(periods, "expense_categories"),
        "cash_flow": [
            {"period": row["period"], "label": row["period_label"], "operating": row["operating_cash_flow"],
             "investing": row["investing_cash_flow"], "financing": row["financing_cash_flow"], "net": row["net_cash_flow"]}
            for row in periods
        ],
        "budget_vs_actual": [
            {"name": "Revenue", "actual": revenue, "budget": budget_revenue, "variance": round(revenue - budget_revenue, 2)},
            {"name": "Cost of sales", "actual": cogs, "budget": budget_cogs, "variance": round(budget_cogs - cogs, 2)},
            {"name": "Operating expenses", "actual": opex, "budget": budget_opex, "variance": round(budget_opex - opex, 2)},
            {"name": "Net profit", "actual": net_profit, "budget": budget_net_profit, "variance": round(net_profit - budget_net_profit, 2)},
        ],
        "accounts": base["accounts"],
        "profitability_summary": [
            {"name": "Gross profit margin", "value": round(gross_profit / revenue * 100, 2) if revenue else 0},
            {"name": "Operating margin", "value": round((gross_profit - opex) / revenue * 100, 2) if revenue else 0},
            {"name": "Net profit margin", "value": round(net_profit / revenue * 100, 2) if revenue else 0},
        ],
        "forecast": base["forecast"],
        "alerts": alerts,
        "source_lineage": base["provenance"],
        "source_window": {"periods": len(periods), "start": periods[0]["period"], "end": periods[-1]["period"]},
    }
