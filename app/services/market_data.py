from __future__ import annotations

import re
import time
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
