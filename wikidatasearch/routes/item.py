from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks, HTTPException
from fastapi_cache.decorator import cache
import time
import traceback

from ..config import settings, SEARCH
from ..dependencies import verify_api_key, limiter, require_descriptive_user_agent
from ..services.logger import Logger


class ItemQuery(BaseModel):
    QID: str = Field(..., example="Q42", description="Wikidata item QID")
    similarity_score: float = Field(..., example=0.95, description="Dot product similarity")
    rrf_score: Optional[float] = Field(None, example=8.43, description="Reciprocal Rank Fusion score")
    source: Optional[str] = Field(None, example="Keyword Search, Vector Search")
    vector: Optional[list[float]] = Field(None, description="Present when return_vectors is True")
    reranker_score: Optional[float] = Field(None, description="Present when rerank is True")


router = APIRouter(
    prefix="/item",
    tags=["Queries"],
    dependencies=[
        Depends(verify_api_key),
        Depends(require_descriptive_user_agent)
    ],
    responses={
        200: {
            "description": "List of relevant Wikidata items sorted by fused similarity scores",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "QID": "Q42",
                            "similarity_score": 0.95,
                            "rrf_score": 0.043,
                            "source": "Vector Search",
                        }
                    ]
                }
            },
        },
        401: {"description": "Missing or invalid API key (if required)"},
        422: {"description": "Missing or invalid parameters"},
        500: {"description": "Internal Server Error"},
    },
)


@router.get(
    "/query/",
    summary="Search Wikidata items with vector and keyword (RRF)",
    operation_id="searchItemsRRF",
    response_model=List[ItemQuery],
)
@cache(expire=settings.CACHE_TTL)
@limiter.limit(settings.RATE_LIMIT)
async def item_query_route(
        request: Request,
        background_tasks: BackgroundTasks,
        query: str = Query(..., example="Douglas Adams", description="Query string to search for"),
        lang: str = Query(
            "all",
            description='Language code for the query. Use "all" to search across all vectors.',
        ),
        K: int = Query(50, description="Number of top results to return"),
        instanceof: Optional[str] = Query(
            None,
            example="Q5,Q634",
            description='Comma separated QIDs to filter by "instance of".',
        ),
        rerank: bool = Query(False, description="If true, apply a reranker model."),
        return_vectors: bool = Query(False, description="If true, include vectors of Wikidata items"),
    ):
    """
    Performs vector and keyword search on Wikidata items, combining results using Reciprocal Rank Fusion (RRF) or an optional reranker model.


    **Args:**

    - **query** (str): Query string to search for.
    - **lang** (str): Language code for the query.
    Use "all" to search across all vectors in the database.
    If a specific language is provided, only vectors in that language will be searched.
    If no vectors exist for that language, the query will be translated to English and searched against all vectors.
    - **K** (int): Number of top results to return.
    - **instanceof** (str, optional): Comma-separated list of QIDs to filter results by a specific "instance of" class.
    - **rerank** (bool): If True, rerank results using a reranker model
    (This option is slower and generally not necessary for RAG applications).
    - **return_vectors** (bool): If True, include vector embeddings in the response.


    **Returns:**

    Each item in the result list includes:

    - **QID** (str): Wikidata QID of the item.
    - **similarity_score** (float): Similarity score (dot product) between the item and the query.
    - **rrf_score** (float): Reciprocal Rank Fusion score combining vector and keyword results.
    - **source** (str): Indicates whether the item was found by "Keyword Search", "Vector Search", or both.
    - **vector** (list[float], optional): Vector embedding of the item, if "return_vectors" is True.
    - **reranker_score** (float, optional): Relevance score from the reranker model, if "rerank" is True.
    """
    start_time = time.time()

    if not query:
        response = "Query is missing"
        Logger.add_request(request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    # Build filter
    filt = {"metadata.IsItem": True}
    if instanceof:
        qids = [qid.strip() for qid in instanceof.split(",") if qid.strip()]
        if not qids:
            response = "Invalid instanceof filter"
            Logger.add_request(request, response, 422, start_time)
            raise HTTPException(status_code=422, detail=response)
        filt["metadata.InstanceOf"] = {"$in": qids}

    try:

        results = SEARCH.search(
            query,
            filter=filt,
            lang=lang.lower(),
            vs_K=K,
            ks_K=max(1, (K + 9) // 10),
            rerank=rerank,
            return_vectors=return_vectors,
        )

        results = results[:K]
        background_tasks.add_task(Logger.add_request, request, "Results", 200, start_time)
        return results

    except Exception as e:
        Logger.add_request(request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
