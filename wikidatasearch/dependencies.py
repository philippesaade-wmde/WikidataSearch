from fastapi import HTTPException, Request, FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

def user_agent_key(request: Request) -> str:
    """
    Rate limit key based on User-Agent.

    If User-Agent is missing or empty, fall back to a shared 'unknown' bucket.
    """
    ua = (request.headers.get("user-agent") or "").strip()

    if not ua:
        # All "no UA" clients share a single bucket
        return "ua:unknown"

    return f"ua:{ua}"

# Consider the user agent for rate limiting since WMcloud requests share the same IP.
limiter = Limiter(key_func=user_agent_key)

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
