from fastapi import Security, HTTPException, Request, FastAPI, Depends
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings


limiter = Limiter(key_func=get_remote_address)
api_key_header = APIKeyHeader(name="X-API-SECRET", auto_error=False)

def verify_api_key(x_api_secret: str = Security(api_key_header)) -> str | None:
    """
    Verify X-API-SECRET against settings.API_SECRET.
    If API_SECRET is unset, auth is effectively disabled.
    """
    if settings.API_SECRET and x_api_secret != settings.API_SECRET:
        raise HTTPException(status_code=401, detail="X-API-SECRET incorrect or missing")
    return x_api_secret

def require_descriptive_user_agent(request: Request) -> None:
    """
    Enforce a descriptive User-Agent.
    Blocks generic HTTP clients.
    """
    ua = request.headers.get("user-agent", "").strip()
    if not ua or " " not in ua or len(ua) < 10:
        raise HTTPException(status_code=400, detail="A more descriptive User-Agent is required")

def register_rate_limit(app: FastAPI) -> None:
    """
    Attach SlowAPI handler. Call once in main.py after creating the app.
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
