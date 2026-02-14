from fastapi import APIRouter, Request, Query, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_cache.decorator import cache
import time

from ..config import settings, SEARCH
from ..services.logger import Logger, Feedback
from ..dependencies import limiter

router = APIRouter(include_in_schema=False)

@limiter.limit(settings.RATE_LIMIT)
@router.get("/")
async def root(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(Logger.add_request, request, 200, time.time())
    return FileResponse(f"{settings.FRONTEND_STATIC_DIR}/index.html")

def mount_static(app):
    app.mount("/assets", StaticFiles(directory=f"{settings.FRONTEND_STATIC_DIR}/assets"), name="frontend-assets")

@router.get("/languages", summary="Supported languages")
@cache(expire=settings.CACHE_TTL)
async def languages():
    vectordb_langs = set(SEARCH.vectorsearch.vectordb_langs)
    other_langs = set(SEARCH.vectorsearch.translator.mint_langs) - vectordb_langs
    return {
        "vectordb_langs": sorted(vectordb_langs),
        "other_langs": sorted(other_langs),
    }

@limiter.limit("10/minute")
@router.post("/feedback", include_in_schema=False)
async def feedback(
    request: Request,
    query: str = Query(..., example="testing"),
    id: str = Query(..., example="Q5"),
    sentiment: str = Query(..., example="up"),
    index: int = Query(..., example=0)):

    Feedback.add_feedback(query, id, sentiment, index)
    return True