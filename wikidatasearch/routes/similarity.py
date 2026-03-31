from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks, HTTPException
from fastapi_cache.decorator import cache
import time
import traceback

from ..config import settings, SEARCH
from ..dependencies import limiter, require_descriptive_user_agent
from ..services.logger import Logger


class SimilarityScore(BaseModel):
    """Represents one similarity score result for a Wikidata entity (With either a QID or PID)."""
    QID: Optional[str] = Field(None, description="Wikidata entity QID")
    PID: Optional[str] = Field(None, description="Wikidata property PID")
    similarity_score: float = Field(..., description="Dot product similarity")
    vector: Optional[list[float]] = Field(None, description="Present when return_vectors is True")

    @model_validator(mode="after")
    def check_id(self):
        """Ensures that exactly one of QID or PID is provided."""
        if (self.QID is None) == (self.PID is None):
            raise ValueError("One of QID or PID must be present")
        return self

router = APIRouter(
    prefix="",
    tags=["Queries"],
    dependencies=[
        Depends(require_descriptive_user_agent)
    ],
    responses={
        200: {
            "description": "List of Wikidata entities with their similarity scores to the query.",
            "content": {
                "application/json": {
                    "example": [
                        {"QID": "Q2", "similarity_score": 0.78},
                        {"QID": "Q36153", "similarity_score": 0.62}
                    ]
                }
            },
        },
        422: {"description": "Missing or invalid parameters"},
        500: {"description": "Internal Server Error"},
    },
)


@router.get(
    "/similarity-score/",
    summary="Compute similarity scores for specific Wikidata QIDs and PIDs",
    operation_id="similarityScoreQuery",
    response_model=List[SimilarityScore],
    response_model_exclude_none=True,
)
@cache(expire=settings.CACHE_TTL)
@limiter.limit(settings.RATE_LIMIT)
async def similarity_score_route(
    request: Request,
    background_tasks: BackgroundTasks,
    query: str = Query(..., examples=["origin of the universe"], description="Query string to compare against Wikidata entities."),
    qid: str = Query(..., examples=["Q42,Q2,Q36153", "Q2"], description="Comma separated list of Wikidata IDs (QIDs and/or PIDs) to compare the query to."),
    lang: str = Query(
        "all",
        description='Language code for the query. Use "all" to compare against all vectors. '
                    'If a specific language is provided, only vectors in that language are used. '
                    'If no vectors exist for that language, the query will be translated to English and compared against all vectors.',
    ),
    return_vectors: bool = Query(False, description="If true, include vector embeddings in the response."),
):
    """
    Computes the similarity score between a query and a specified list of Wikidata entities.


    **Args:**

    - **query** (str): Query string to compare against Wikidata entities.
    - **qid** (str): Comma-separated list of Wikidata IDs (QIDs and/or PIDs)
    to compare the query to.
    - **lang** (str): Language code for the query.
    Use "all" to compare with all vectors in the database.
    If a specific language is provided, only vectors in that language will be used.
    If no vectors exist for that language, the query will be translated to English and compared against all vectors.
    - **return_vectors** (bool): Currently unavailable; if set to True this endpoint
    returns HTTP 422.


    **Returns:**

    Each item in the result list includes:

    - **QID**/**PID** (str): Wikidata entity ID of the compared entity.
    - **similarity_score** (float): Similarity score (dot product) between the entity and the query.
    - **vector** (list[float], optional): Vector embedding of the entity.
    Currently omitted because `return_vectors` is disabled.
    """
    start_time = time.time()

    if not query:
        response = "Query is missing"
        Logger.add_request(request, 422, start_time, error=response)
        raise HTTPException(status_code=422, detail=response)

    if not qid:
        response = "QIDs are missing"
        Logger.add_request(request, 422, start_time, error=response)
        raise HTTPException(status_code=422, detail=response)

    qids = [q.strip() for q in qid.split(",") if q.strip()]
    if not qids:
        response = "No valid QIDs provided"
        Logger.add_request(request, 422, start_time, error=response)
        raise HTTPException(status_code=422, detail=response)

    if len(qids) > 100:
        response = "Too many QIDs provided. Please provide 100 or fewer QIDs."
        Logger.add_request(request, 422, start_time, error=response)
        raise HTTPException(status_code=422, detail=response)

    try:
        results = SEARCH.get_similarity_scores(
            query=query,
            qids=qids,
            lang=lang,
            return_vectors=return_vectors,
        )

        background_tasks.add_task(Logger.add_request, request, 200, start_time)
        return results

    except Exception as e:
        Logger.add_request(request, 500, start_time, error=str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
