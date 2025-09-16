import time
import os
import traceback
import math

# Import necessary types and classes from FastAPI and other libraries.
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .logger import Logger, Feedback
from .search import HybridSearch

# Retrieve the frontend static directory path from environment variables, falling back to a default if not set.
FRONTEND_STATIC_DIR = os.environ.get("FRONTEND_STATIC_DIR", "./frontend/dist")
API_SECRET = os.environ.get("API_SECRET")
CACHE_TTL = 180  # 3 minutes

app = FastAPI(
    title="Wikidata Vector Search",
    description="An API for querying Wikidata Vector Database.",
    version="1.0.0",
    openapi_tags=[{"name": "Queries", "description": "Endpoints for querying data"}],
    openapi_url="/openapi.json",
    docs_url="/docs",  # Change the Swagger UI path if needed
    redoc_url="/redoc",  # Change the ReDoc path if needed
    swagger_ui_parameters={"persistAuthorization": True},
)

# Enable all Cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Set up rate limiting
limiter = Limiter(key_func=lambda request: request.client.host)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize the cache on startup
@app.on_event("startup")
async def startup_event():
    FastAPICache.init(InMemoryBackend(), prefix="wikidata-cache")

# Serve static files from the '/assets' endpoint,
#   pulling from the frontend static directory.
app.mount(
    "/assets",
    StaticFiles(directory=f"{FRONTEND_STATIC_DIR}/assets"),
    name="frontend-assets",
)

search = HybridSearch(os.environ,
                      dest_lang='en',
                      vectordb_langs=['en', 'fr'])


@app.get("/", include_in_schema=False)
async def root(request: Request, background_tasks: BackgroundTasks):
    """
    Serve the main HTML file for the root endpoint.

    Returns:
        FileResponse: The index.html file from the frontend static directory.
    """

    background_tasks.add_task(Logger.add_request, request, '', 200, 0)
    return FileResponse(f"{FRONTEND_STATIC_DIR}/index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serve the favicon.ico file.

    Returns:
        FileResponse: The favicon.ico file from the frontend static directory.
    """
    return FileResponse(f"{FRONTEND_STATIC_DIR}/favicon.ico")

@app.get("/languages", include_in_schema=False)
async def languages():
    vectordb_langs = set(search.vectorsearch.vectordb_langs)
    other_langs = set(search.vectorsearch.translator.mint_langs)
    other_langs = other_langs - vectordb_langs
    return {
        'vectordb_langs': sorted(list(vectordb_langs)),
        'other_langs': sorted(list(other_langs))
    }

@app.post("/feedback", include_in_schema=False)
async def feedback(
    request: Request,
    query: str = Query(..., example="testing"),
    qid: str = Query(..., example="Q5"),
    sentiment: str = Query(..., example="up"),
    index: int = Query(..., example=0)):

    Feedback.add_feedback(query, qid, sentiment, index)
    return True

@app.get(
    "/item/query/",
    responses={
        200: {
            "description": "Returns a list of relevant Wikidata item QIDs with similarity scores",
            "content": {
                "application/json": {
                    "example": [{"QID": "Q42", "similarity_score": 0.95}]
                }
            },
        },
        401: {
            "description": "Invalid API secret",
            "content": {
                "application/json": {
                    "example": {"detail": "X-API-SECRET incorrect or missing"}
                }
            },
        },
        422: {
            "description": "Missing query parameter",
            "content": {
                "application/json": {"example": {"detail": "Query is missing"}}
            },
        },
    },
)
@cache(expire=CACHE_TTL)  # If cache is used, the request will not be logged
@limiter.limit("10/minute")
async def item_query_route(
    request: Request, background_tasks: BackgroundTasks,
    x_api_secret: str | None = Header(None, description="API key for authentication"),
    query: str = Query(..., example="testing"),
    instanceof: str = Query(None, example="Q5,Q634"),
    lang: str = 'en',
    K: int = 20,
    rerank: bool = False,
    return_vectors: bool = False,
):
    """
    Query on Wikidata items in the Vector Database.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        instanceof (str): Optional QIDs to filter results by instance of a specific class.
        lang (str): The language of the query.
        K (int): The number of top results to return.
        rerank (bool): Whether to rerank the results based on relevance.
        return_vectors (bool): Whether to return the vector embeddings of the items.

    Returns:
        list: A list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if not request.headers.get('user-agent'):
        response = "User-Agent is required"
        background_tasks.add_task(Logger.add_request, request, response, 400, start_time)
        raise HTTPException(status_code=400, detail=response)

    if API_SECRET and (API_SECRET != x_api_secret):
        response = "X-API-SECRET incorrect or missing"
        background_tasks.add_task(Logger.add_request, request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        background_tasks.add_task(Logger.add_request, request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    filter={"metadata.IsItem": True}

    if instanceof:
        instanceof = instanceof.split(",")
        instanceof = [qid.strip() for qid in instanceof]
        filter["metadata.InstanceOf"] = {"$in": instanceof}

    try:
        results = search.search(
            query,
            filter=filter,
            lang=lang,
            vs_K=K,
            ks_K=math.ceil(K/10),
            rerank=rerank,
            return_vectors=return_vectors
        )

        results = results[:K]

        background_tasks.add_task(Logger.add_request, request, 'Results', 200, start_time)
        return results
    except Exception as e:
        background_tasks.add_task(Logger.add_request, request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get(
    "/property/query/",
    responses={
        200: {
            "description": "Returns a list of relevant Wikidata property PIDs with similarity scores",
            "content": {
                "application/json": {
                    "example": [{
                        "PID": "P31",
                        "similarity_score": 0.89
                    }]
                }
            },
        },
        401: {
            "description": "Invalid API secret",
            "content": {
                "application/json": {
                    "example": {"detail": "X-API-SECRET incorrect or missing"}
                }
            },
        },
        422: {
            "description": "Missing query parameter",
            "content": {
                "application/json": {
                    "example": {"detail": "Query is missing"}
                }
            },
        },
    },
)
@cache(expire=CACHE_TTL)  # If cache is used, the request will not be logged
@limiter.limit("10/minute")
async def property_query_route(
    request: Request, background_tasks: BackgroundTasks,
    x_api_secret: str | None = Header(None, description="API key for authentication"),
    query: str = Query(..., example="testing"),
    instanceof: str = Query(None, example="Q18616576"),
    lang: str = 'en',
    K: int = 50,
    rerank: bool = False,
    return_vectors: bool = False,
):
    """
    Query on Wikidata properties in the Vector Database.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        instanceof (str): Optional QIDs to filter results by instance of a specific class.
        lang (str): The source language of the query.
        K (int): The number of top results to return.
        rerank (bool): Whether to rerank the results based on relevance.
        return_vectors (bool): Whether to return the vector embeddings of the properties.

    Returns:
        list: A list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if not request.headers.get('user-agent'):
        response = "User-Agent is required"
        background_tasks.add_task(Logger.add_request, request, response, 400, start_time)
        raise HTTPException(status_code=400, detail=response)

    if API_SECRET and (API_SECRET != x_api_secret):
        response = "X-API-SECRET incorrect or missing"
        background_tasks.add_task(Logger.add_request, request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        background_tasks.add_task(Logger.add_request, request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    filter={"metadata.IsProperty": True}

    if instanceof:
        instanceof = instanceof.split(",")
        instanceof = [qid.strip() for qid in instanceof]
        filter["metadata.InstanceOf"] = {"$in": instanceof}

    try:
        results = search.search(
            query,
            filter=filter,
            lang=lang,
            vs_K=K,
            ks_K=math.ceil(K/10),
            rerank=rerank,
            return_vectors=return_vectors
        )

        results = results[:K]

        background_tasks.add_task(Logger.add_request, request, 'Results', 200, start_time)
        return results
    except Exception as e:
        background_tasks.add_task(Logger.add_request, request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get(
    "/similarity-score/",
    responses={
        200: {
            "description": "Returns a list sorted by similarity scores, for a given query and specified list of Wikidata entities.",
            "content": {
                "application/json": {
                    "example": [{
                        "QID": "Q2",
                        "similarity_score": 0.78
                    }]
                }
            },
        },
        401: {
            "description": "Invalid API secret",
            "content": {
                "application/json": {
                    "example": {"detail": "X-API-SECRET incorrect or missing"}
                }
            },
        },
        422: {
            "description": "Missing query or qid parameter",
            "content": {
                "application/json": {
                    "example": {"detail": "Query or QID is missing"}
                }
            },
        },
    },
)
@cache(expire=CACHE_TTL)  # If cache is used, the request will not be logged
@limiter.limit("10/minute")
async def similarity_score_route(
    request: Request, background_tasks: BackgroundTasks,
    x_api_secret: str | None = Header(None, description="API key for authentication"),
    query: str = Query(..., example="testing"),
    qid: str = Query(..., example="Q42,Q2,Q36153"),
    lang: str = 'en',
    return_vectors: bool = False,
):
    """
    Get the similarity score for a given query and a specified list of Wikidata entities.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        qid (str): A list of QIDs (comma separated) to compare the query to.
        lang (str): The source language of the query.
        return_vectors (bool): Whether to return the vector embeddings of the items.

    Returns:
        list: A sorted list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if not request.headers.get('user-agent'):
        response = "User-Agent is required"
        background_tasks.add_task(Logger.add_request, request, response, 400, start_time)
        raise HTTPException(status_code=400, detail=response)

    if API_SECRET and (API_SECRET != x_api_secret):
        response = "X-API-SECRET incorrect or missing"
        background_tasks.add_task(Logger.add_request, request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        background_tasks.add_task(Logger.add_request, request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    if not qid:
        response = "QIDs are missing"
        background_tasks.add_task(Logger.add_request, request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    try:
        qids = qid.split(",")
        qids = [q.strip() for q in qids]

        results = search.vectorsearch.get_similarity_scores(
            query,
            qids,
            lang=lang,
            return_vectors=return_vectors
        )

        background_tasks.add_task(Logger.add_request, request, 'Results', 200, start_time)
        return results
    except Exception as e:
        background_tasks.add_task(Logger.add_request, request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
