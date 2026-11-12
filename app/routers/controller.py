from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.controller_finance import build_controller_dashboard

router = APIRouter(prefix="/controller", tags=["controller-finance"])


@router.get("/dashboard")
def controller_dashboard(
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
    entity: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
):
    try:
        return build_controller_dashboard(db, from_date=from_date, to_date=to_date, entity=entity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
