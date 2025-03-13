import os  # Import the os module to interact with the operating system.

from typing import Annotated

# Import necessary types and classes from FastAPI and other libraries.
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Header
import requests

from .logger import get_logger
from .jina import JinaAIAPIEmbedder
from .datastax import AstraDBConnect

# Create logger instance from base logger config in `logger.py`
logger = get_logger(__name__)  # Initialize a logger for this module.

# Retrieve the frontend static directory path from environment variables, falling back to a default if not set.
FRONTEND_STATIC_DIR = os.environ.get('FRONTEND_STATIC_DIR', './frontend/dist')
API_SECRET = os.environ.get('API_SECRET', 'Thou shall [not] pass')

app = FastAPI()  # Create an instance of the FastAPI application.

# Serve static files from the '/assets' endpoint,
#   pulling from the frontend static directory.
app.mount(
    "/assets",
    StaticFiles(directory=f"{FRONTEND_STATIC_DIR}/assets"),
    name="frontend-assets"
)

jina_api_key = os.environ.get('JINA_API_KEY')
embedding_model = JinaAIAPIEmbedder(api_key=jina_api_key)
astradb = AstraDBConnect(os.environ, embedding_model)

def get_wikidata_items(qids, language="en"):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "format": "json",
        "ids": "|".join(qids),
        "props": "labels|descriptions|claims"
    }

    response = requests.get(url, params=params)
    data = response.json()

    result = {}
    for qid in qids:
        if "entities" not in data or qid not in data["entities"]:
            result[qid] = {"error": "Invalid QID or item not found"}
            continue

        entity = data["entities"][qid]
        label = entity.get("labels", {}).get(language, {}).get("value", "No label available")
        description = entity.get("descriptions", {}).get(language, {}).get("value", "No description available")
        image_filename = None
        if "P18" in entity.get("claims", {}):
            image_filename = entity["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"]
            image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_filename}"
        else:
            image_url = "No image available"

        result[qid] = {
            "label": label,
            "description": description,
            "image": image_url
        }

    return result

@app.get("/")
async def root():
    """
    Serve the main HTML file for the root endpoint.

    Returns:
        FileResponse: The index.html file from the frontend static directory.
    """
    return FileResponse(f"{FRONTEND_STATIC_DIR}/index.html")


@app.get("/favicon.ico")
async def favicon():
    """
    Serve the favicon.ico file.

    Returns:
        FileResponse: The favicon.ico file from the frontend static directory.
    """
    return FileResponse(f"{FRONTEND_STATIC_DIR}/favicon.ico")

# Add a route where the vector is given instead of a query.

# Add a route where no vector is given by instead a filter option.

# Add parameters like language, is_property, K, filter by QID.
# Return the embedding of the items as well.
@app.get("/query")
async def query(
        x_api_secret: Annotated[str, Header()], query):
    """
    Query the Wikidata Vector Database.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        top_k (int, optional): The number of top results to return.
            Defaults to 10.
        lang (str, optional): The language code for the query processing
            ('en' for English, 'de' for German). Defaults to 'en'

    Raises:
        ValueError: If the provided language is not supported
            (not 'en' or 'de').

    Returns:
        list: A list of dictionaries containing QIDs and the similarity scores.
    """
    if not API_SECRET in [x_api_secret, 'Thou shall [not] pass']:
        logger.debug(f'{API_SECRET=}')
        # raise ValueError("API key is missing or incorrect")

    logger.debug(f'{query=}')
    results = astradb.get_similar_qids(query, K=10, filter={})

    seen = set()
    output = [{
        'QID': r[0].metadata['QID'],
        'similarity_score': r[1]
    } for r in results if r[0].metadata['QID'] not in seen and not seen.add(r[0].metadata['QID'])]

    qids = [i['QID'] for i in output]
    wikidata = get_wikidata_items(qids)
    output = [{
        **r,
        **wikidata[r['QID']]
    } for r in output]
    logger.debug(f'{qids=}')
    return output