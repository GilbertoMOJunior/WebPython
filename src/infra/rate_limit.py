# Gilberto Mota de Oliveira Junior
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

limiter = Limiter(key_func=get_remote_address)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    if "minute" in exc.detail:
        retry_after = 60
    elif "hour" in exc.detail:
        retry_after = 3600
    elif "second" in exc.detail:
        retry_after = 1
    elif "day" in exc.detail:
        retry_after = 86400
    else:
        retry_after = 60

    response = Response(
        content=f'{{"error": "Rate limit exceeded", "message": "Too many requests. Limit: {exc.detail}", "retry_after": {retry_after}, "timestamp": "{datetime.now(timezone.utc).isoformat()}"}}',
        status_code=429,
        media_type="application/json"
    )
    response.headers["X-RateLimit-Limit"] = str(exc.detail)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(int(datetime.now(timezone.utc).timestamp()) + retry_after)
    response.headers["Retry-After"] = str(retry_after)
    return response

RATE_LIMITS = {
    "critical":    os.getenv("RATE_LIMIT_CRITICAL",    "5/minute"),
    "restrictive": os.getenv("RATE_LIMIT_RESTRICTIVE", "20/minute"),
    "moderate":    os.getenv("RATE_LIMIT_MODERATE",    "100/minute"),
    "low":         os.getenv("RATE_LIMIT_LOW",         "200/minute"),
    "light":       os.getenv("RATE_LIMIT_LIGHT",       "300/minute"),
    "default":     os.getenv("RATE_LIMIT_DEFAULT",     "50/minute"),
}

def get_rate_limit(endpoint_type: str) -> str:
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])
