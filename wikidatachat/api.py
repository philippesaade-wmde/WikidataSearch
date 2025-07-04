from typing import Annotated
import time
import os
import traceback

# Import necessary types and classes from FastAPI and other libraries.
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .logger import Logger
from .jina import JinaAIAPI
from .datastax import AstraDBConnect
from .translator import Translator
from .wikidata import get_text_by_id

# Retrieve the frontend static directory path from environment variables, falling back to a default if not set.
FRONTEND_STATIC_DIR = os.environ.get("FRONTEND_STATIC_DIR", "./frontend/dist")
API_SECRET = os.environ.get("API_SECRET", "Thou shall [not] pass")

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

# Serve static files from the '/assets' endpoint,
#   pulling from the frontend static directory.
app.mount(
    "/assets",
    StaticFiles(directory=f"{FRONTEND_STATIC_DIR}/assets"),
    name="frontend-assets",
)

translator = Translator('en', ['en', 'de'])
jina_api_key = os.environ.get("JINA_API_KEY")
embedding_model = JinaAIAPI(api_key=jina_api_key)
astradb = AstraDBConnect(os.environ, embedding_model)


@app.get("/", include_in_schema=False)
async def root():
    """
    Serve the main HTML file for the root endpoint.

    Returns:
        FileResponse: The index.html file from the frontend static directory.
    """
    return FileResponse(f"{FRONTEND_STATIC_DIR}/index.html")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serve the favicon.ico file.

    Returns:
        FileResponse: The favicon.ico file from the frontend static directory.
    """
    return FileResponse(f"{FRONTEND_STATIC_DIR}/favicon.ico")


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
async def item_query_route(
    request: Request,
    x_api_secret: Annotated[
        str, Header(..., required=True, description="API key for authentication")
    ],
    query: str = Query(..., example="testing"),
    src_lang: str = 'en',
    K: int = 10,
    rerank: bool = True,
):
    """
    Query on Wikidata items in the Vector Database.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.

    Returns:
        list: A list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if API_SECRET != x_api_secret:
        response = "X-API-SECRET incorrect or missing"
        Logger.add_request(request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        Logger.add_request(request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)


    try:
        query = translator.translate(query, src_lang=src_lang)

        vector_results = astradb.vector_similar_qids(
            query,
            K=K,
            filter={"metadata.IsItem": True}
        )

        keyword_results = astradb.keyword_similar_qids(
            query,
            K=K,
            filter={"metadata.IsItem": True}
        )

        results = astradb.reciprocal_rank_fusion({
            'Vector Search': vector_results,
            'Keyword Search': keyword_results
        })

        for i in range(len(results)):
            results[i]['text'] = get_text_by_id(results[i]['QID'])

        if rerank:
            results = embedding_model.rerank(query, results)

        Logger.add_request(request, results, 200, start_time)
        return results
    except Exception as e:
        Logger.add_request(request, str(e), 500, start_time)
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
async def property_query_route(
    request: Request,
    x_api_secret: Annotated[
        str, Header(..., required=True, description="API key for authentication")
    ],
    query: str = Query(..., example="testing"),
    src_lang: str = 'en',
    K: int = 10,
    rerank: bool = True,
):
    """
    Query on Wikidata properties in the Vector Database.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.

    Returns:
        list: A list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if API_SECRET != x_api_secret:
        response = "X-API-SECRET incorrect or missing"
        Logger.add_request(request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        Logger.add_request(request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    try:
        query = translator.translate(query, src_lang=src_lang)

        vector_results = astradb.vector_similar_qids(
            query,
            K=K,
            filter={"metadata.IsProperty": True}
        )

        keyword_results = astradb.keyword_similar_qids(
            query,
            K=K,
            filter={"metadata.IsItem": True}
        )

        results = astradb.reciprocal_rank_fusion({
            'Vector Search': vector_results,
            'Keyword Search': keyword_results
        })

        for i in range(len(results)):
            results[i]['text'] = get_text_by_id(results[i]['QID'])

        if rerank:
            results = embedding_model.rerank(query, results)

        Logger.add_request(request, results, 200, start_time)
        return results
    except Exception as e:
        Logger.add_request(request, str(e), 500, start_time)
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
async def similarity_score_route(
    request: Request,
    x_api_secret: Annotated[
        str, Header(..., required=True, description="API key for authentication")
    ],
    query: str = Query(..., example="testing"),
    qid: str = Query(..., example="Q42,Q2,Q36153"),
    src_lang: str = 'en',
):
    """
    Get the similarity score for a given query and a specified list of Wikidata entities.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        qid (str): A list of QIDs (comma separated) to compare the query to.

    Returns:
        list: A sorted list of dictionaries containing QIDs and the similarity scores.
    """

    start_time = time.time()
    if API_SECRET != x_api_secret:
        response = "X-API-SECRET incorrect or missing"
        Logger.add_request(request, response, 401, start_time)
        raise HTTPException(status_code=401, detail=response)

    if not query:
        response = "Query is missing"
        Logger.add_request(request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    if not qid:
        response = "QIDs are missing"
        Logger.add_request(request, response, 422, start_time)
        raise HTTPException(status_code=422, detail=response)

    try:
        query = translator(query, src_lang=src_lang)

        qids = qid.split(",")
        qids = [q.strip() for q in qids]

        filter = {'$or':
            [
                {'metadata.QID': qid} if qid[0]=='Q' else {'metadata.PID': qid}
                for qid in qids
            ]
        }

        results = astradb.get_similar_qids(
            query,
            filter=filter
        )

        Logger.add_request(request, results, 200, start_time)
        return results
    except Exception as e:
        Logger.add_request(request, str(e), 500, start_time)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")
