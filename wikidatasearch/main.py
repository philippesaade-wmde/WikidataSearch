# ruff: noqa: D100,D101,D102,D103,D104,D200,D205,D417
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from gradio.routes import mount_gradio_app

from .config import settings
from .dependencies import register_rate_limit
from .routes import frontend, health, item, property, similarity
from .services.analytics import build_analytics_app

app = FastAPI(
    title="Wikidata Vector Search",
    description="API for querying the Wikidata Vector Database",
    version="0.2.1",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
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

register_rate_limit(app)

# Initialize the cache on startup
@app.on_event("startup")
async def startup_event():
    FastAPICache.init(InMemoryBackend(), prefix="wikidata-cache")

# Routers
app.include_router(item.router)
app.include_router(property.router)
app.include_router(similarity.router)
app.include_router(frontend.router)
app.include_router(health.router)

frontend.mount_static(app)

if settings.ANALYTICS_API_SECRET:
    mount_gradio_app(
        app,
        build_analytics_app(),
        path=f"/admin/{settings.ANALYTICS_API_SECRET}"
    )