"""
Authentication and Rate Limiting Middleware
- Internal requests (from known hosts): Unlimited, no auth required
- External requests: Require API key, rate limited
"""
import time
from typing import Optional
from collections import defaultdict
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from eafw_api.config import get_settings

settings = get_settings()

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Internal/trusted hosts - unlimited access without auth
TRUSTED_HOSTS = {
    "127.0.0.1",
    "localhost",
    "eafw_cms",
    "eafw_mapviewer",
    "eafw_nginx",
    "eafw_jobs",
    "eafw_mapserver",
    "eafw_tileserv",
    "eafw_pgbouncer",
    # Docker network
    "172.17.0.0/16",
    "10.0.0.0/8",
    "192.168.0.0/16",
}

# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(lambda: {"count": 0, "reset_time": 0})

# Rate limit settings
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW = 60  # seconds


def is_trusted_host(client_ip: str) -> bool:
    """Check if request is from a trusted internal host"""
    if client_ip in TRUSTED_HOSTS:
        return True

    # Check network ranges
    for network in TRUSTED_HOSTS:
        if "/" in network:
            # Simple CIDR check (for production, use ipaddress module)
            network_prefix = network.split("/")[0].rsplit(".", 1)[0]
            if client_ip.startswith(network_prefix):
                return True

    return False


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies"""
    # Check X-Forwarded-For header (from nginx/proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for external requests.
    Internal/trusted hosts bypass rate limiting.
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = get_client_ip(request)

        # Skip rate limiting for trusted hosts
        if is_trusted_host(client_ip):
            return await call_next(request)

        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)

        # Check rate limit
        current_time = time.time()
        client_data = rate_limit_storage[client_ip]

        # Reset if window expired
        if current_time > client_data["reset_time"]:
            client_data["count"] = 0
            client_data["reset_time"] = current_time + RATE_LIMIT_WINDOW

        # Check if over limit
        if client_data["count"] >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds",
                    "retry_after": int(client_data["reset_time"] - current_time),
                },
                headers={
                    "Retry-After": str(int(client_data["reset_time"] - current_time)),
                    "X-RateLimit-Limit": str(RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(client_data["reset_time"])),
                },
            )

        # Increment count
        client_data["count"] += 1

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(
            RATE_LIMIT_REQUESTS - client_data["count"]
        )
        response.headers["X-RateLimit-Reset"] = str(int(client_data["reset_time"]))

        return response


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[str]:
    """
    Verify API key for external requests.
    Internal/trusted hosts bypass API key check.
    """
    client_ip = get_client_ip(request)

    # Trusted hosts don't need API key
    if is_trusted_host(client_ip):
        return "internal"

    # External requests require API key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key (in production, check against database)
    # For now, accept any non-empty key for demo
    # TODO: Implement proper API key validation from database
    valid_keys = {
        "demo-key-123",  # Demo key for testing
        # Add more keys or load from database
    }

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key",
        )

    return api_key


def require_api_key():
    """Dependency to require API key for a route"""
    return Security(verify_api_key)
