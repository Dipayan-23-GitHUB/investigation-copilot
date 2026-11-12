from __future__ import annotations

import csv
import html
import io
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from openpyxl import load_workbook

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_SERIES = ["DCOILBRENTEU", "DTWEXBGS"]
WORLD_BANK_LANDING = "https://www.worldbank.org/en/research/commodity-markets"
WORLD_BANK_FALLBACK_XLSX = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
    "CMO-Historical-Data-Monthly.xlsx"
)
CACHE_TTL = {"fred": 6 * 60 * 60, "worldbank": 24 * 60 * 60}
_FAILURE_TTL = 15 * 60
_CACHE: dict[str, dict[str, Any]] = {}


class PublicMarketError(RuntimeError):
    pass


def clear_cache() -> None:
    _CACHE.clear()


def _cache_get(key: str, loader, ttl: int) -> tuple[Any, bool]:
    now = time.monotonic()
    cached = _CACHE.get(key)
    if cached and cached["expires_at"] > now:
        if cached.get("value") is None:
            raise PublicMarketError(cached.get("error") or "Data source is temporarily unavailable.")
        return cached["value"], bool(cached.get("stale"))
    try:
        value = loader()
        _CACHE[key] = {
            "value": value, "expires_at": now + ttl, "stale": False,
            "fetched_at": now,
        }
        return value, False
    except Exception as exc:
        # Avoid hammering a provider when it is temporarily down. Keep prior successful
        # content for a limited stale window and make the stale state visible to the UI.
        if cached:
            age = now - cached.get("fetched_at", 0)
            if cached.get("value") is not None and age <= 7 * 24 * 60 * 60:
                cached["expires_at"] = now + _FAILURE_TTL
                cached["stale"] = True
                return cached["value"], True
        _CACHE[key] = {
            "value": None,
            "expires_at": now + _FAILURE_TTL,
            "stale": False,
            "error": str(exc)[:240],
        }
        raise PublicMarketError(str(exc)) from exc


def _fetch_fred_csv() -> dict[str, list[dict[str, Any]]]:
    response = httpx.get(
        FRED_CSV_URL,
        params={"id": ",".join(FRED_SERIES)},
        headers={"User-Agent": "InvestigationCopilot/1.0 (internal finance dashboard)"},
        timeout=20.0,
        follow_redirects=True,
    )
    response.raise_for_status()
    text = response.text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise PublicMarketError("FRED returned an empty CSV response.")
    date_key = next((x for x in reader.fieldnames if x.lower() in {"observation_date", "date"}), None)
    if not date_key:
        raise PublicMarketError("FRED CSV did not contain a date column.")
    result: dict[str, list[dict[str, Any]]] = {series: [] for series in FRED_SERIES}
    for row in reader:
        date_value = (row.get(date_key) or "").strip()
        if not date_value:
            continue
        for series in FRED_SERIES:
            raw = (row.get(series) or "").strip()
            if raw in {"", ".", "NA", "N/A"}:
                continue
            try:
                value = float(raw.replace(",", ""))
            except ValueError:
                continue
            result[series].append({"date": date_value, "value": value})
    for series, points in result.items():
        points.sort(key=lambda p: p["date"])
        if not points:
            raise PublicMarketError(f"No observations were returned for FRED series {series}.")
        result[series] = points[-400:]
    return result


def _find_world_bank_xlsx_url() -> str:
    response = httpx.get(WORLD_BANK_LANDING, timeout=20.0, follow_redirects=True)
    response.raise_for_status()
    page = response.text
    candidates = re.findall(r"href\s*=\s*['\"]([^'\"]*CMO-Historical-Data-Monthly\.xlsx[^'\"]*)['\"]", page, re.I)
    for candidate in candidates:
        url = html.unescape(candidate)
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return "https://www.worldbank.org" + url
        if url.startswith("http"):
            return url
    # The landing-page pattern may change; a current known World Bank release path is a fallback.
    return WORLD_BANK_FALLBACK_XLSX


def _month_from_header(values: list[Any]) -> str | None:
    text_parts = []
    for value in values:
        if value is None:
            continue
        if hasattr(value, "strftime"):
            try:
                return value.strftime("%Y-%m")
            except Exception:
                pass
        text_parts.append(str(value).strip())
    combined = " ".join(text_parts)
    patterns = [
        r"(?P<y>20\d{2}|19\d{2})\s*[mM]\s*(?P<m>1[0-2]|0?[1-9])",
        r"(?P<y>20\d{2}|19\d{2})[-_/](?P<m>1[0-2]|0?[1-9])",
        r"(?P<m>1[0-2]|0?[1-9])[-_/](?P<y>20\d{2}|19\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            return f"{int(match.group('y')):04d}-{int(match.group('m')):02d}"
    month_names = {
        "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
        "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7,
        "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    }
    tokens = re.findall(r"[A-Za-z]+|\d{4}", combined)
    months = [month_names[t.lower()] for t in tokens if t.lower() in month_names]
    year = next((int(t) for t in tokens if t.isdigit() and len(t) == 4 and 1900 <= int(t) <= 2100), None)
    # Ignore annual/quarterly/ranged labels such as "Jan-Dec 2025" or "Apr-Jun 2026".
    if len(set(months)) == 1 and year:
        return f"{year:04d}-{months[0]:02d}"
    return None


def parse_world_bank_monthly_xlsx(content: bytes) -> dict[str, dict[str, Any]]:
    """Parse Gold and Silver rows from the World Bank Pink Sheet monthly workbook.

    Supports the common wide-format export (Commodity/Unit plus monthly columns) and
    multi-row month/year headers. If the publisher materially changes the layout, fail
    closed rather than guessing a price/date pairing.
    """
    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    try:
        parsed: dict[str, dict[str, Any]] = {}
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 3:
                continue
            header_candidates = []
            for ridx, row in enumerate(rows[:15]):
                labels = [str(v).strip().lower() for v in row if v is not None]
                if any("commodity" in v for v in labels) and any("unit" in v for v in labels):
                    header_candidates.append(ridx)
            if not header_candidates:
                continue
            header_idx = header_candidates[0]
            headers = rows[header_idx]
            name_col = next((i for i, v in enumerate(headers) if v and "commodity" in str(v).lower()), 0)
            unit_col = next((i for i, v in enumerate(headers) if v and "unit" in str(v).lower()), 1)
            date_cols: dict[int, str] = {}
            for col in range(len(headers)):
                # Pink Sheet exports can place year labels above the Commodity/Unit row
                # and month labels beneath it. Inspect a small header window on both sides.
                header_rows = list(range(max(0, header_idx - 4), min(len(rows), header_idx + 4)))
                combined = [rows[r][col] if col < len(rows[r]) else None for r in header_rows]
                month = _month_from_header(combined)
                if month:
                    date_cols[col] = month
            if not date_cols:
                continue
            for row in rows[header_idx + 1:]:
                if name_col >= len(row) or row[name_col] is None:
                    continue
                commodity = str(row[name_col]).strip().lower()
                key = "gold" if commodity == "gold" or commodity.startswith("gold,") else "silver" if commodity == "silver" or commodity.startswith("silver,") else None
                if not key:
                    continue
                unit = str(row[unit_col]).strip() if unit_col < len(row) and row[unit_col] is not None else "USD per troy ounce"
                points = []
                for col, period in date_cols.items():
                    if col >= len(row):
                        continue
                    raw = row[col]
                    try:
                        value = float(raw)
                    except (TypeError, ValueError):
                        continue
                    if value <= 0:
                        continue
                    points.append({"date": period, "value": value})
                points.sort(key=lambda p: p["date"])
                if points:
                    # Preserve the publisher's exact unit. Convert cents to dollars only
                    # when the unit label explicitly identifies cents.
                    if "cent" in unit.lower():
                        points = [{**p, "value": p["value"] / 100.0} for p in points]
                        unit = unit.replace("cents", "USD").replace("cent", "USD")
                    parsed[key] = {"unit": unit, "series": points[-36:]}
            if len(parsed) == 2:
                break
        if set(parsed) != {"gold", "silver"}:
            raise PublicMarketError("Could not identify both Gold and Silver monthly rows in the World Bank workbook.")
        return parsed
    finally:
        wb.close()


def _fetch_world_bank_metals() -> dict[str, dict[str, Any]]:
    xlsx_url = _find_world_bank_xlsx_url()
    response = httpx.get(xlsx_url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    parsed = parse_world_bank_monthly_xlsx(response.content)
    for item in parsed.values():
        item["source_url"] = xlsx_url
    return parsed


def _card(points: list[dict[str, Any]], *, unit: str, source: str, frequency: str, stale: bool = False) -> dict[str, Any]:
    points = sorted(points, key=lambda p: p["date"])
    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    change = latest["value"] - previous["value"] if previous else None
    change_pct = (change / previous["value"] * 100) if previous and previous["value"] else None
    return {
        "status": "available", "value": latest["value"], "change": change,
        "change_percent": change_pct, "date": latest["date"], "unit": unit,
        "frequency": frequency, "source": source, "stale": stale,
        "series": points[-100:],
    }


def _unavailable(detail: str, *, unit: str | None = None, source: str | None = None) -> dict[str, Any]:
    return {"status": "unavailable", "detail": detail, "unit": unit, "source": source}


def public_market_dashboard() -> dict[str, Any]:
    """Low-cost internal reference dashboard using openly documented public series.

    Restricted index/VIX feeds are deliberately not scraped or substituted with proxies.
    """
    cards: dict[str, Any] = {}
    notes = [
        "Reference observations only; data may be delayed and are not execution quotes.",
        "Brent is EIA daily spot data distributed by FRED. The U.S. Dollar card is the Federal Reserve Nominal Broad U.S. Dollar Index, not ICE DXY.",
        "Gold and Silver are monthly World Bank Pink Sheet averages; they are not daily spot prices.",
        "Direct Dow, S&P 500, Nasdaq Composite and VIX tiles remain unavailable until their index-display permissions are confirmed. No unofficial scraping or ETF proxy substitution is used.",
    ]
    try:
        fred, fred_stale = _cache_get("fred_multi", _fetch_fred_csv, CACHE_TTL["fred"])
        cards["brent"] = _card(fred["DCOILBRENTEU"], unit="USD per barrel", source="EIA via FRED · DCOILBRENTEU", frequency="Daily spot", stale=fred_stale)
        cards["usd_index"] = _card(fred["DTWEXBGS"], unit="Index Jan 2006=100 · not DXY", source="Federal Reserve via FRED · DTWEXBGS", frequency="Daily", stale=fred_stale)
    except PublicMarketError as exc:
        cards["brent"] = _unavailable(f"EIA/FRED feed unavailable: {exc}", unit="USD per barrel", source="EIA via FRED")
        cards["usd_index"] = _unavailable(f"Federal Reserve/FRED feed unavailable: {exc}", unit="Broad USD index points", source="Federal Reserve via FRED")

    try:
        metals, wb_stale = _cache_get("worldbank_metals", _fetch_world_bank_metals, CACHE_TTL["worldbank"])
        cards["gold"] = _card(metals["gold"]["series"], unit=metals["gold"]["unit"], source="World Bank Pink Sheet", frequency="Monthly average", stale=wb_stale)
        cards["silver"] = _card(metals["silver"]["series"], unit=metals["silver"]["unit"], source="World Bank Pink Sheet", frequency="Monthly average", stale=wb_stale)
    except PublicMarketError as exc:
        cards["gold"] = _unavailable(f"World Bank monthly commodity feed unavailable: {exc}", unit="USD per troy ounce", source="World Bank Pink Sheet")
        cards["silver"] = _unavailable(f"World Bank monthly commodity feed unavailable: {exc}", unit="USD per troy ounce", source="World Bank Pink Sheet")

    license_detail = "Direct index series not activated: confirm data-display rights with the index owner/provider before connecting."
    cards["us_stocks"] = {
        "status": "unavailable",
        "items": {
            "dow": _unavailable(license_detail, unit="Index points", source="Dow Jones / S&P Dow Jones Indices"),
            "sp500": _unavailable(license_detail, unit="Index points", source="S&P Dow Jones Indices"),
            "nasdaq": _unavailable(license_detail, unit="Index points", source="Nasdaq"),
        },
        "detail": license_detail,
    }
    cards["vix"] = _unavailable(
        "CBOE VIX data-display rights are not configured. Connect an authorized CBOE-licensed feed.",
        unit="Index points", source="CBOE",
    )
    cards["market_mood"] = _unavailable(
        "Not calculated because the licensed VIX input is unavailable; no synthetic sentiment label is shown."
    )

    available = sum(1 for key in ("gold", "silver", "brent", "usd_index") if cards.get(key, {}).get("status") == "available")
    return {
        "cards": cards,
        "source": "FRED/EIA + World Bank Pink Sheet",
        "frequency": "Daily and monthly reference observations",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "available_cards": available,
        "notes": notes,
        "cache_policy": {
            "FRED daily series": "6 hours; one combined request for Brent and broad USD index",
            "World Bank commodity series": "24 hours; one monthly workbook download for Gold and Silver",
            "provider_failure": "Failed refresh suppressed for 15 minutes; previous successful cache may be served stale for up to 7 days with stale=true",
        },
    }
