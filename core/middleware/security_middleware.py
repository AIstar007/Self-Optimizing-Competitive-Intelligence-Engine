"""Security middleware for CORS, rate limiting, and security headers."""

import logging
import time
from typing import Dict, Optional
from collections import defaultdict

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for CORS security headers."""

    def __init__(
        self,
        app,
        allowed_origins: Optional[list] = None,
        allowed_methods: Optional[list] = None,
        allowed_headers: Optional[list] = None,
        allow_credentials: bool = True,
        max_age: int = 3600,
    ):
        """Initialize middleware."""
        super().__init__(app)
        self.allowed_origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:8000",
        ]
        self.allowed_methods = allowed_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
        ]
        self.allowed_headers = allowed_headers or [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._handle_preflight(request)

        # Call next middleware
        response = await call_next(request)

        # Add CORS headers
        self._add_cors_headers(request, response)

        return response

    def _handle_preflight(self, request: Request) -> Response:
        """Handle CORS preflight request."""
        origin = request.headers.get("origin")

        if not self._is_origin_allowed(origin):
            return Response(status_code=403)

        response = Response(status_code=200)
        self._add_cors_headers(request, response)
        return response

    def _add_cors_headers(self, request: Request, response: Response) -> None:
        """Add CORS headers to response."""
        origin = request.headers.get("origin")

        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.allowed_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                self.allowed_headers
            )
            response.headers["Access-Control-Max-Age"] = str(self.max_age)

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return True

        return origin in self.allowed_origins or "*" in self.allowed_origins


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers."""

    def __init__(app):
        """Initialize middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers[
            "Content-Security-Policy"
        ] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        """Initialize middleware."""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

        # Track requests per client
        self.client_requests: Dict[str, list] = defaultdict(list)
        self.client_blocks: Dict[str, float] = {}

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        client_id = self._get_client_id(request)

        # Check if client is blocked
        if client_id in self.client_blocks:
            if time.time() < self.client_blocks[client_id]:
                raise HTTPException(status_code=429, detail="Too many requests")
            else:
                del self.client_blocks[client_id]

        # Check rate limits
        current_time = time.time()
        one_minute_ago = current_time - 60
        one_hour_ago = current_time - 3600

        # Clean old requests
        if client_id in self.client_requests:
            self.client_requests[client_id] = [
                t for t in self.client_requests[client_id] if t > one_hour_ago
            ]

        # Count requests
        requests_this_minute = sum(
            1
            for t in self.client_requests[client_id]
            if t > one_minute_ago
        )
        requests_this_hour = len(self.client_requests[client_id])

        # Check limits
        if (
            requests_this_minute >= self.requests_per_minute
            or requests_this_hour >= self.requests_per_hour
        ):
            # Block client for 1 hour
            self.client_blocks[client_id] = current_time + 3600
            raise HTTPException(status_code=429, detail="Too many requests")

        # Record request
        self.client_requests[client_id].append(current_time)

        # Call next middleware
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - requests_this_minute - 1)
        )
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))

        return response

    @staticmethod
    def _get_client_id(request: Request) -> str:
        """Get client ID from request."""
        # Try to get from user first
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Fall back to IP
        if request.client:
            return f"ip:{request.client.host}"

        return "unknown"


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Middleware for input validation."""

    # Max request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        "DROP TABLE",
        "DELETE FROM",
        "INSERT INTO",
        "UPDATE TABLE",
        "SELECT * FROM",
        "<script>",
        "</script>",
        "javascript:",
        "onclick=",
        "onerror=",
    ]

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        # Check body size
        if "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.MAX_BODY_SIZE:
                raise HTTPException(status_code=413, detail="Request body too large")

        # Check for suspicious patterns in URL
        if self._contains_suspicious_pattern(request.url.path):
            logger.warning(
                f"Suspicious pattern detected in URL: {request.url.path}"
            )
            raise HTTPException(status_code=400, detail="Invalid request")

        # Check for suspicious patterns in query params
        for key, value in request.query_params.items():
            if self._contains_suspicious_pattern(str(value)):
                logger.warning(
                    f"Suspicious pattern detected in query: {key}={value}"
                )
                raise HTTPException(status_code=400, detail="Invalid request")

        # Call next middleware
        response = await call_next(request)

        return response

    def _contains_suspicious_pattern(self, value: str) -> bool:
        """Check if value contains suspicious pattern."""
        value_upper = value.upper()
        for pattern in self.SUSPICIOUS_PATTERNS:
            if pattern in value_upper:
                return True
        return False


class HTTPSEnforcementMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing HTTPS."""

    def __init__(self, app, enabled: bool = True):
        """Initialize middleware."""
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        if self.enabled and request.url.scheme != "https":
            # In development, allow http
            if request.client.host not in ["127.0.0.1", "localhost"]:
                raise HTTPException(
                    status_code=403,
                    detail="HTTPS required",
                )

        response = await call_next(request)
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware for adding request ID to responses."""

    import uuid

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        # Get or create request ID
        request_id = request.headers.get("X-Request-ID") or str(self.uuid.uuid4())

        # Attach to request state
        request.state.request_id = request_id

        # Call next middleware
        response = await call_next(request)

        # Add request ID header
        response.headers["X-Request-ID"] = request_id

        return response


class TrustedHostsMiddleware(BaseHTTPMiddleware):
    """Middleware for trusted hosts validation."""

    def __init__(self, app, trusted_hosts: Optional[list] = None):
        """Initialize middleware."""
        super().__init__(app)
        self.trusted_hosts = trusted_hosts or [
            "localhost",
            "127.0.0.1",
            "*.example.com",
        ]

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        host = request.headers.get("host", "")

        if not self._is_trusted_host(host):
            logger.warning(f"Request from untrusted host: {host}")
            raise HTTPException(status_code=403, detail="Untrusted host")

        response = await call_next(request)
        return response

    def _is_trusted_host(self, host: str) -> bool:
        """Check if host is trusted."""
        # Remove port if present
        host_without_port = host.split(":")[0]

        for trusted in self.trusted_hosts:
            if trusted.startswith("*"):
                # Wildcard matching
                suffix = trusted[1:]
                if host_without_port.endswith(suffix):
                    return True
            elif host_without_port == trusted:
                return True

        return False
