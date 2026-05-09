# Gilberto Mota de Oliveira Junior
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from datetime import datetime, timezone
from settings import (
    RATE_LIMIT_CRITICAL,
    RATE_LIMIT_MODERATE,
    RATE_LIMIT_RESTRICTIVE,
    RATE_LIMIT_LOW,
    RATE_LIMIT_LIGHT,
    RATE_LIMIT_DEFAULT,
)

# Criar limiter com base no IP do cliente
limiter = Limiter(key_func=get_remote_address)

# Handler personalizado para exceção de rate limit
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler personalizado para quando o rate limit é excedido.
    Retorna uma resposta JSON formatada em vez de erro HTML.
    """
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
        content=(
            f'{{"error": "Rate limit exceeded", '
            f'"message": "Muitas requisições. Limite: {exc.detail}", '
            f'"retry_after": {retry_after}, '
            f'"timestamp": "{datetime.now(timezone.utc).isoformat()}"}}'
        ),
        status_code=429,
        media_type="application/json"
    )
    response.headers["X-RateLimit-Limit"] = str(exc.detail)
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(
        int(datetime.now(timezone.utc).timestamp()) + retry_after
    )
    response.headers["Retry-After"] = str(retry_after)
    return response

# Configuração de limites por perfil
RATE_LIMITS = {
    "critical": RATE_LIMIT_CRITICAL,       # Login, logout, exclusões sensíveis
    "restrictive": RATE_LIMIT_RESTRICTIVE, # Criações, atualizações
    "moderate": RATE_LIMIT_MODERATE,       # Listagens, buscas por ID
    "low": RATE_LIMIT_LOW,                 # Health checks, endpoints de sistema
    "light": RATE_LIMIT_LIGHT,             # Endpoints públicos, documentação
    "default": RATE_LIMIT_DEFAULT,         # Padrão
}

def get_rate_limit(endpoint_type: str) -> str:
    """Retorna o rate limit para um tipo de endpoint"""
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["default"])
