"""Liveness and readiness endpoints for service monitoring."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from ..services.logger import engine

router = APIRouter(tags=["Health"])

@router.get("/health/live", include_in_schema=False)
def live():
    """Return a liveness signal when the API process is running."""
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
def ready():
    """Return readiness status based on database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Not ready")
