from pydantic_settings import BaseSettings, SettingsConfigDict
from .services.search import HybridSearch

class Settings(BaseSettings):
    """Application settings loaded from environment variables or defaults."""

    FRONTEND_STATIC_DIR: str = "./frontend/dist"
    CACHE_TTL: int = 180  # 3 minutes
    RATE_LIMIT: str = "30/minute"
    DEST_LANG: str = "en"
    VECTORDb_LANGS: list[str] = ["en", "fr", "ar"]

    # --- From .env ---
    ASTRA_DB_APPLICATION_TOKEN: str | None = None
    ASTRA_DB_API_ENDPOINT: str | None = None
    ASTRA_DB_DATABASE_ID: str | None = None
    ASTRA_DB_KEYSPACE: str | None = None
    ASTRA_DB_COLLECTION: str | None = None

    JINA_API_KEY: str | None = None

    API_SECRET: str | None = None
    ANALYTICS_API_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Instantiate settings from .env
settings = Settings()

SEARCH = HybridSearch(
    api_keys={
        "ASTRA_DB_APPLICATION_TOKEN": settings.ASTRA_DB_APPLICATION_TOKEN,
        "ASTRA_DB_API_ENDPOINT": settings.ASTRA_DB_API_ENDPOINT,
        "ASTRA_DB_DATABASE_ID": settings.ASTRA_DB_DATABASE_ID,
        "ASTRA_DB_KEYSPACE": settings.ASTRA_DB_KEYSPACE,
        "ASTRA_DB_COLLECTION": settings.ASTRA_DB_COLLECTION,
        "JINA_API_KEY": settings.JINA_API_KEY,
    },
    dest_lang=settings.DEST_LANG,
    vectordb_langs=settings.VECTORDb_LANGS
)