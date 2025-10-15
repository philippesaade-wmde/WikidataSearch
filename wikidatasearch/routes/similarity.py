from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks, HTTPException
from fastapi_cache.decorator import cache
import time
import traceback

from ..config import settings, SEARCH
from ..dependencies import verify_api_key, limiter, require_descriptive_user_agent
from ..services.logger import Logger


class SimilarityScore(BaseModel):
    QID: str = Field(..., example="Q2", description="Wikidata entity QID")
    similarity_score: float = Field(..., example=0.78, description="Dot product similarity")
    vector: Optional[list[float]] = Field(None, description="Present when return_vectors is True")


router = APIRouter(
    prefix="",
    tags=["Queries"],
    dependencies=[
        Depends(verify_api_key),
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
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Missing or invalid parameters"},
        500: {"description": "Internal Server Error"},
    },
)


@router.get(
    "/similarity-score/",
    summary="Compute similarity scores for specific Wikidata QIDs",
    operation_id="similarityScoreQuery",
    response_model=List[SimilarityScore],
    response_model_exclude_none=True,
)
@cache(expire=settings.CACHE_TTL)
@limiter.limit(settings.RATE_LIMIT)
async def similarity_score_route(
    request: Request,
    background_tasks: BackgroundTasks,
    query: str = Query(..., example="origin of the universe", description="Query string to compare against Wikidata entities."),
    qid: str = Query(..., example="Q42,Q2,Q36153", description="Comma separated list of Wikidata QIDs to compare the query to."),
    lang: str = Query(
        "en",
        description='Language code for the query. Use "all" to compare against all vectors. '
                    'If a specific language is provided, only vectors in that language are used. '
                    'If no vectors exist for that language, the query will be translated to English and compared against all vectors.',
    ),
    return_vectors: bool = Query(False, description="If True, include vector embeddings in the response."),
):
    """
    Computes the similarity score between a query and a specified list of Wikidata entities.


    **Args:**

    - **query** (str): Query string to compare against Wikidata entities.
    - **qid** (str): Comma-separated list of Wikidata QIDs to compare the query to.
    - **lang** (str): Language code for the query.
    Use "all" to compare with all vectors in the database.
    If a specific language is provided, only vectors in that language will be used.
    If no vectors exist for that language, the query will be translated to English and compared against all vectors.
    - **return_vectors** (bool): If True, include vector embeddings in the response.


    **Returns:**

    Each item in the result list includes:

    - **QID** (str): Wikidata QID of the compared entity.
    - **similarity_score** (float): Similarity score (dot product) between the entity and the query.
    - **vector** (list[float], optional): Vector embedding of the entity, if "return_vectors" is True.
    """
    start_time = time.time()

    require_descriptive_user_agent(request)

    if not query:
        detail = "Query is missing"
        Logger.add_request(request, detail, 422, start_time)
        raise HTTPException(status_code=422, detail=detail)

    if not qid:
        detail = "QIDs are missing"
        Logger.add_request(request, detail, 422, start_time)
        raise HTTPException(status_code=422, detail=detail)

    try:
        qids = [q.strip() for q in qid.split(",") if q.strip()]
        if not qids:
            detail = "No valid QIDs provided"
            Logger.add_request(request, detail, 422, start_time)
            raise HTTPException(status_code=422, detail=detail)

        results = SEARCH.vectorsearch.get_similarity_scores(
            query=query,
            qids=qids,
            lang=lang,
            return_vectors=return_vectors,
        )

        background_tasks.add_task(Logger.add_request, request, "Results", 200, start_time)
        return results

    except Exception as e:
        Logger.add_request(request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
