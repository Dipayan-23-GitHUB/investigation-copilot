from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..services.market_data import MarketDataError, equity_history, metals_overview, search_equities
from ..services.public_market_dashboard import PublicMarketError, public_market_dashboard

router = APIRouter(prefix="/market", tags=["market-intelligence"])


def _run(callable_, *args):
    try:
        return callable_(*args)
    except MarketDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/search")
def market_search(q: str = Query(min_length=2, max_length=80)):
    return _run(search_equities, q)


@router.get("/equity")
def market_equity(symbol: str = Query(min_length=1, max_length=32)):
    return _run(equity_history, symbol)


@router.get("/metals")
def market_metals():
    result = _run(metals_overview)
    if not result["items"] and result["errors"]:
        first = result["errors"][0]
        raise HTTPException(status_code=first["status_code"], detail=first["detail"])
    return result


@router.get("/dashboard")
def market_dashboard_view():
    # Public, low-cost reference sources; this endpoint does not consume Alpha Vantage quota.
    try:
        return public_market_dashboard()
    except PublicMarketError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
