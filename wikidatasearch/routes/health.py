# ruff: noqa: D100,D101,D102,D103,D104,D200,D205,D417
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..services.logger import engine

router = APIRouter(tags=["Health"])

@router.get("/health/live", include_in_schema=False)
def live():
    return {"status": "ok"}

@router.get("/health/ready", include_in_schema=False)
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")