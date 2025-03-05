import os  # Import the os module to interact with the operating system.

from typing import Annotated

# Import necessary types and classes from FastAPI and other libraries.
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Header

# Import custom modules for the RAG pipeline and logging.
from .logger import get_logger

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


@app.get("/query")
async def query(
        x_api_secret: Annotated[str, Header()], query):
    """
    Handle the API requests to process and respond with relevant information based on the query.

    Args:
        x_api_secret (str): API Secret to confirm user is authorised.
        query (str): The query string to be processed.
        top_k (int, optional): The number of top results to return.
            Defaults to 10.
        lang (str, optional): The language code for the query processing
            ('en' for English, 'de' for German). Defaults to 'en'.

    Raises:
        ValueError: If the provided language is not supported
            (not 'en' or 'de').

    Returns:
        dict: A dictionary containing the 'answer' and 'sources'
            based on the query processing.
    """
    if not API_SECRET in [x_api_secret, 'Thou shall [not] pass']:
        logger.debug(f'{API_SECRET=}')
        # raise ValueError("API key is missing or incorrect")

    # Log the input parameters for debugging.
    logger.debug(f'{query=}')

    # Return the processed answer and sources.
    return {
        "answer": query
    }
