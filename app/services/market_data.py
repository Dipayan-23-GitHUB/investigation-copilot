from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import settings

BASE_URL = "https://www.alphavantage.co/query"
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9.^=_-]{1,32}$")


class MarketDataError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _cached_get(cache_key: str, params: dict[str, str], ttl_seconds: int) -> dict[str, Any]:
    if not settings.alpha_vantage_api_key:
        raise MarketDataError(
            "Market data is not configured. Add MARKET_DATA_API_KEY to the Render web service environment.",
            503,
        )

    now = time.monotonic()
    cached = _CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1]

    request_params = {**params, "apikey": settings.alpha_vantage_api_key}
    try:
        response = httpx.get(BASE_URL, params=request_params, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except httpx.TimeoutException as exc:
        raise MarketDataError("Market data provider timed out. Try again later.", 504) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise MarketDataError("Could not retrieve market data from the configured provider.", 502) from exc

    if not isinstance(payload, dict):
        raise MarketDataError("Market data provider returned an unexpected response.", 502)

    provider_message = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
    if provider_message and not any(k in payload for k in ("bestMatches", "Meta Data", "data", "Time Series (Daily)")):
        low = str(provider_message).lower()
        if "call frequency" in low or "rate limit" in low or "25 requests" in low or "limit" in low:
            raise MarketDataError("Market data provider rate limit reached. Cached data may become available later.", 429)
        if "premium" in low or "subscription" in low or "premium endpoint" in low:
            raise MarketDataError("This index series requires an Alpha Vantage premium subscription.", 403)
        raise MarketDataError("Market data provider could not fulfil this request. Check the symbol or provider account.", 502)

    _CACHE[cache_key] = (now + ttl_seconds, payload)
    return payload


def search_equities(query: str) -> dict[str, Any]:
    term = query.strip()
    if len(term) < 2 or len(term) > 80:
        raise MarketDataError("Search text must contain between 2 and 80 characters.", 422)
    payload = _cached_get(
        f"search:{term.casefold()}",
        {"function": "SYMBOL_SEARCH", "keywords": term},
        6 * 60 * 60,
    )
    matches = payload.get("bestMatches", [])
    results = []
    for item in matches[:10] if isinstance(matches, list) else []:
        results.append({
            "symbol": item.get("1. symbol"),
            "name": item.get("2. name"),
            "type": item.get("3. type"),
            "region": item.get("4. region"),
            "market_open": item.get("5. marketOpen"),
            "market_close": item.get("6. marketClose"),
            "timezone": item.get("7. timezone"),
            "currency": item.get("8. currency"),
            "match_score": item.get("9. matchScore"),
        })
    return {"items": results, "count": len(results), "source": "Alpha Vantage", "data_frequency": "Daily end-of-day history"}


def equity_history(symbol: str) -> dict[str, Any]:
    normalized = symbol.strip().upper()
    if not _SYMBOL_RE.fullmatch(normalized):
        raise MarketDataError("Invalid ticker symbol. Use letters, numbers, dots, hyphens or carets only.", 422)
    payload = _cached_get(
        f"equity:{normalized}",
        {"function": "TIME_SERIES_DAILY", "symbol": normalized, "outputsize": "compact"},
        6 * 60 * 60,
    )
    series_key = next((key for key in payload if key.startswith("Time Series (")), None)
    raw_series = payload.get(series_key, {}) if series_key else {}
    if not isinstance(raw_series, dict) or not raw_series:
        raise MarketDataError("No daily price history was returned for this ticker. Verify the provider symbol and exchange suffix.", 404)

    points = []
    for date_key, values in raw_series.items():
        if not isinstance(values, dict):
            continue
        def number(*keys: str):
            for key in keys:
                value = values.get(key)
                if value not in (None, ""):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None
            return None
        points.append({
            "date": str(date_key),
            "open": number("1. open"),
            "high": number("2. high"),
            "low": number("3. low"),
            "close": number("4. close"),
            "volume": number("5. volume"),
        })
    points.sort(key=lambda x: x["date"])
    if not points:
        raise MarketDataError("The ticker response contained no usable daily observations.", 502)
    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    prior_close = previous["close"] if previous else None
    change = latest["close"] - prior_close if prior_close is not None and latest["close"] is not None else None
    change_pct = (change / prior_close * 100) if change is not None and prior_close not in (None, 0) else None
    meta = payload.get("Meta Data", {})
    return {
        "symbol": normalized,
        "name": normalized,
        "last_refreshed": meta.get("3. Last Refreshed") or latest["date"],
        "timezone": meta.get("5. Time Zone"),
        "currency": None,
        "latest": latest,
        "previous_close": prior_close,
        "change": change,
        "change_percent": change_pct,
        "series": points[-100:],
        "source": "Alpha Vantage",
        "frequency": "Daily end-of-day OHLCV; not a real-time quote",
        "source_url": "https://www.alphavantage.co/documentation/",
    }


METALS = {
    "GOLD": {"label": "Gold", "function": "GOLD_SILVER_HISTORY", "interval": "daily", "unit": "USD per troy ounce", "ttl": 6 * 60 * 60},
    "SILVER": {"label": "Silver", "function": "GOLD_SILVER_HISTORY", "interval": "daily", "unit": "USD per troy ounce", "ttl": 6 * 60 * 60},
    "COPPER": {"label": "Copper", "function": "COPPER", "interval": "monthly", "unit": "USD per metric ton", "ttl": 24 * 60 * 60},
    "ALUMINUM": {"label": "Aluminum", "function": "ALUMINUM", "interval": "monthly", "unit": "USD per metric ton", "ttl": 24 * 60 * 60},
}


def _metal_series(symbol: str) -> dict[str, Any]:
    config = METALS[symbol]
    params = {"function": config["function"]}
    if symbol in {"GOLD", "SILVER"}:
        params["symbol"] = symbol
    params["interval"] = config["interval"]
    payload = _cached_get(f"metal:{symbol}", params, config["ttl"])

    raw = payload.get("data", [])
    points = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            date_value = item.get("date") or item.get("timestamp")
            price_value = item.get("value") or item.get("price") or item.get("close")
            try:
                price = float(price_value)
            except (TypeError, ValueError):
                continue
            if date_value:
                points.append({"date": str(date_value), "value": price})
    elif isinstance(raw, dict):
        for date_value, price_value in raw.items():
            try:
                price = float(price_value)
            except (TypeError, ValueError):
                continue
            points.append({"date": str(date_value), "value": price})
    points.sort(key=lambda x: x["date"])
    if not points:
        raise MarketDataError(f"No {config['label'].lower()} history was returned by the provider.", 502)
    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    change = latest["value"] - previous["value"] if previous else None
    change_pct = change / previous["value"] * 100 if previous and previous["value"] else None
    meta = payload.get("Meta Data", {})
    return {
        "symbol": symbol,
        "label": config["label"],
        "interval": config["interval"],
        "unit": meta.get("Unit") or config["unit"],
        "latest": latest,
        "previous": previous,
        "change": change,
        "change_percent": change_pct,
        "series": points[-60:],
        "source": "Alpha Vantage",
        "source_detail": "Gold and silver: historical daily observations. Copper and aluminum: IMF global price series via FRED, monthly.",
        "last_refreshed": meta.get("Last Refreshed") or latest["date"],
    }


def metals_overview() -> dict[str, Any]:
    items = []
    errors = []
    for symbol in METALS:
        try:
            items.append(_metal_series(symbol))
        except MarketDataError as exc:
            errors.append({"symbol": symbol, "detail": str(exc), "status_code": exc.status_code})
    return {
        "items": items,
        "count": len(items),
        "errors": errors,
        "source": "Alpha Vantage",
        "data_note": "Gold and silver use daily historical observations; copper and aluminum use monthly global price series. These are reference indicators, not executable exchange quotes.",
    }


def clear_market_cache() -> None:
    """Test helper; not exposed as a public endpoint."""
    _CACHE.clear()


INDEXES = {
    "dow": {"label": "Dow Jones Industrial Average", "symbol": "DJI"},
    "sp500": {"label": "S&P 500", "symbol": "SPX"},
    "nasdaq": {"label": "Nasdaq Composite", "symbol": "COMP"},
    "vix": {"label": "CBOE Volatility Index", "symbol": "VIX"},
}


def _normalize_reference_points(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize AV commodity/index `data` lists without guessing missing values."""
    raw = payload.get("data", [])
    points: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            date_value = item.get("date") or item.get("timestamp")
            value = item.get("value") or item.get("close") or item.get("4. close")
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if date_value:
                points.append({"date": str(date_value), "value": number})
    elif isinstance(raw, dict):
        for date_value, item in raw.items():
            if isinstance(item, dict):
                value = item.get("4. close") or item.get("close") or item.get("value")
            else:
                value = item
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            points.append({"date": str(date_value), "value": number})
    if not points:
        # Some time-series endpoints use a named key instead of `data`.
        series_key = next((k for k in payload if k.startswith("Time Series")), None)
        raw_series = payload.get(series_key, {}) if series_key else {}
        if isinstance(raw_series, dict):
            for date_value, item in raw_series.items():
                if not isinstance(item, dict):
                    continue
                try:
                    number = float(item.get("4. close") or item.get("close") or item.get("value"))
                except (TypeError, ValueError):
                    continue
                points.append({"date": str(date_value), "value": number})
    points.sort(key=lambda x: x["date"])
    return points


def _index_history(key: str) -> dict[str, Any]:
    config = INDEXES[key]
    payload = _cached_get(
        f"index:{config['symbol']}",
        {"function": "INDEX_DATA", "symbol": config["symbol"], "interval": "daily"},
        6 * 60 * 60,
    )
    points = _normalize_reference_points(payload)
    if not points:
        raise MarketDataError(f"No daily observations were returned for {config['label']}.", 502)
    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    change = latest["value"] - previous["value"] if previous else None
    change_pct = (change / previous["value"] * 100) if previous and previous["value"] else None
    return {
        "status": "available", "label": config["label"], "symbol": config["symbol"],
        "value": latest["value"], "change": change, "change_percent": change_pct,
        "date": latest["date"], "unit": "Index points", "frequency": "Daily close",
        "series": points[-100:], "source": "Alpha Vantage", "source_url": "https://www.alphavantage.co/documentation/",
    }


def _brent_history() -> dict[str, Any]:
    payload = _cached_get("commodity:BRENT", {"function": "BRENT", "interval": "daily"}, 6 * 60 * 60)
    points = _normalize_reference_points(payload)
    if not points:
        raise MarketDataError("No daily Brent crude observations were returned by the provider.", 502)
    latest = points[-1]
    previous = points[-2] if len(points) > 1 else None
    change = latest["value"] - previous["value"] if previous else None
    change_pct = (change / previous["value"] * 100) if previous and previous["value"] else None
    meta = payload.get("Meta Data", {})
    return {
        "status": "available", "label": "Brent Crude", "symbol": "BRENT",
        "latest": latest, "value": latest["value"], "change": change, "change_percent": change_pct,
        "date": latest["date"], "unit": meta.get("Unit") or "USD per barrel",
        "frequency": "Daily reference price", "series": points[-100:],
        "source": "Alpha Vantage / EIA via FRED",
    }


def _as_dashboard_item(item: dict[str, Any]) -> dict[str, Any]:
    latest = item.get("latest") or {}
    if not latest and item.get("value") is not None:
        latest = {"value": item.get("value"), "date": item.get("date")}
    if "value" in latest:
        value = latest.get("value")
        date = latest.get("date")
    else:
        value = latest.get("close")
        date = latest.get("date")
    return {
        "status": "available", "value": value, "change": item.get("change"),
        "change_percent": item.get("change_percent"), "date": date,
        "unit": item.get("unit") or item.get("frequency") or "Daily close",
        "frequency": item.get("interval") or item.get("frequency") or "Daily close",
    }


def market_dashboard() -> dict[str, Any]:
    """Return reference-led market tiles. Missing or premium feeds remain unavailable."""
    cards: dict[str, Any] = {}
    notes = [
        "Prices are provider observations, not real-time execution quotes.",
        "Dow, S&P 500, Nasdaq Composite and VIX use Alpha Vantage index endpoints that require a premium subscription.",
        "DXY is not available in this adapter; no unrelated currency ETF or proxy is substituted.",
        "Market Mood is a simple internal VIX-based label, not a provider consensus or investment recommendation.",
    ]
    stock_items: dict[str, Any] = {}
    stock_errors: list[str] = []
    for key in ("dow", "sp500", "nasdaq"):
        try:
            stock_items[key] = _index_history(key)
        except MarketDataError as exc:
            stock_items[key] = {"status": "unavailable", "detail": str(exc), "symbol": INDEXES[key]["symbol"]}
            stock_errors.append(str(exc))
    cards["us_stocks"] = {
        "status": "available" if any(x.get("status") == "available" for x in stock_items.values()) else "unavailable",
        "items": stock_items,
        "detail": "Daily index close data. Premium index access is required for direct Dow, S&P 500 and Nasdaq Composite feeds.",
    }

    for key, fn in (("gold", lambda: _metal_series("GOLD")), ("silver", lambda: _metal_series("SILVER")), ("brent", _brent_history)):
        try:
            cards[key] = _as_dashboard_item(fn())
        except MarketDataError as exc:
            cards[key] = {"status": "unavailable", "detail": str(exc)}

    cards["usd_index"] = {
        "status": "unavailable",
        "detail": "DXY is not supplied by the current Alpha Vantage adapter. Connect a licensed U.S. Dollar Index feed to enable this tile.",
        "unit": "DXY index points",
    }

    try:
        vix = _index_history("vix")
        cards["vix"] = vix
        vix_value = float(vix["value"])
        if vix_value < 15:
            mood = "Calm"
        elif vix_value < 20:
            mood = "Balanced"
        elif vix_value < 30:
            mood = "Cautious"
        else:
            mood = "Defensive"
        cards["market_mood"] = {
            "status": "available", "label": mood, "vix_value": vix_value,
            "method": "Internal heuristic from latest VIX close: <15 Calm · 15–<20 Balanced · 20–<30 Cautious · ≥30 Defensive.",
        }
    except MarketDataError as exc:
        cards["vix"] = {"status": "unavailable", "detail": str(exc), "symbol": "VIX"}
        cards["market_mood"] = {"status": "unavailable", "detail": "A VIX reading is required before this derived mood label can be calculated."}

    return {
        "cards": cards,
        "source": "Alpha Vantage",
        "frequency": "Daily close / daily reference observations",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": notes,
    }
