"""Audit logging middleware for tracking API requests and responses."""

import logging
import json
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.infrastructure.security.audit_logger import (
    get_audit_logger,
    AuditLogger,
    AuditEventType,
    AuditSeverity,
)

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of API requests and responses."""

    # Endpoints that should be audited
    AUDITED_PATHS = [
        "/api/v1/security",
        "/api/v1/users",
        "/api/v1/data",
        "/api/v1/integrations",
    ]

    # Methods that should be audited
    AUDITED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    # Sensitive fields to mask in audit logs
    SENSITIVE_FIELDS = {
        "password",
        "token",
        "api_key",
        "secret",
        "credit_card",
        "ssn",
        "private_key",
    }

    def __init__(self, app):
        """Initialize middleware."""
        super().__init__(app)
        self.audit_logger = None

    async def dispatch(self, request: Request, call_next):
        """Process request and log to audit."""
        # Initialize audit logger
        if self.audit_logger is None:
            self.audit_logger = get_audit_logger()

        # Check if endpoint should be audited
        if not self._should_audit(request):
            return await call_next(request)

        start_time = time.time()
        user_id = self._get_user_id(request)

        try:
            # Capture request data
            request_data = await self._capture_request_data(request)

            # Call next middleware/endpoint
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log audit event
            await self._log_audit_event(
                request=request,
                response=response,
                user_id=user_id,
                request_data=request_data,
                duration=duration,
                success=response.status_code < 400,
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error event
            self.audit_logger.log_event(
                event_type=AuditEventType.API_ERROR,
                user_id=user_id,
                resource_type="api",
                resource_id=request.url.path,
                action=request.method,
                status="failure",
                severity=AuditSeverity.WARNING,
                context={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "duration": duration,
                    "error": str(e),
                    "ip": request.client.host if request.client else None,
                },
            )

            raise

    def _should_audit(self, request: Request) -> bool:
        """Check if request should be audited."""
        # Only audit configured paths
        if not any(
            request.url.path.startswith(path) for path in self.AUDITED_PATHS
        ):
            return False

        # Only audit certain methods
        if request.method not in self.AUDITED_METHODS:
            return False

        return True

    @staticmethod
    def _get_user_id(request: Request) -> Optional[str]:
        """Get user ID from request."""
        if hasattr(request.state, "user_id"):
            return request.state.user_id
        return None

    async def _capture_request_data(self, request: Request) -> dict:
        """Capture request data."""
        data = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
        }

        # Capture body if present
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        data["body"] = json.loads(body)
                    except json.JSONDecodeError:
                        data["body"] = body.decode()
        except Exception as e:
            logger.warning(f"Failed to capture request body: {e}")

        # Mask sensitive data
        self._mask_sensitive_data(data)

        return data

    async def _log_audit_event(
        self,
        request: Request,
        response: Response,
        user_id: Optional[str],
        request_data: dict,
        duration: float,
        success: bool,
    ) -> None:
        """Log audit event."""
        # Determine event type
        path = request.url.path
        if "users" in path and request.method == "POST":
            event_type = AuditEventType.USER_CREATED
        elif "roles" in path and request.method == "POST":
            event_type = AuditEventType.ROLE_CREATED
        elif "data" in path and request.method == "POST":
            event_type = AuditEventType.DATA_CREATED
        elif "data" in path and request.method == "PUT":
            event_type = AuditEventType.DATA_UPDATED
        elif "data" in path and request.method == "DELETE":
            event_type = AuditEventType.DATA_DELETED
        elif "integrations" in path and request.method == "POST":
            event_type = AuditEventType.INTEGRATION_CREATED
        elif "integrations" in path and request.method == "PUT":
            event_type = AuditEventType.INTEGRATION_UPDATED
        elif "integrations" in path and request.method == "DELETE":
            event_type = AuditEventType.INTEGRATION_DELETED
        else:
            event_type = AuditEventType.SYSTEM_CONFIG_CHANGED

        # Determine severity based on status code
        if response.status_code >= 500:
            severity = AuditSeverity.CRITICAL
        elif response.status_code >= 400:
            severity = AuditSeverity.WARNING
        else:
            severity = AuditSeverity.INFO

        # Log event
        self.audit_logger.log_event(
            event_type=event_type,
            user_id=user_id,
            resource_type="api",
            resource_id=path,
            action=request.method,
            status="success" if success else "failure",
            severity=severity,
            context={
                "status_code": response.status_code,
                "duration": f"{duration:.3f}s",
                "request_data": request_data,
                "ip": request.client.host if request.client else None,
                "changes": {"status_code": response.status_code},
            },
        )

    def _mask_sensitive_data(self, data: dict) -> None:
        """Mask sensitive fields in data."""
        if isinstance(data, dict):
            for key, value in data.items():
                if any(
                    sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS
                ):
                    data[key] = "***MASKED***"
                elif isinstance(value, dict):
                    self._mask_sensitive_data(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._mask_sensitive_data(item)


class RequestResponseLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""

    def __init__(self, app):
        """Initialize middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request and log."""
        # Log request
        logger.debug(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # Call next middleware/endpoint
        response = await call_next(request)

        # Log response
        logger.debug(
            f"Outgoing response: {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response


class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking errors and exceptions."""

    def __init__(self, app):
        """Initialize middleware."""
        super().__init__(app)
        self.audit_logger = None

    async def dispatch(self, request: Request, call_next):
        """Process request and track errors."""
        if self.audit_logger is None:
            self.audit_logger = get_audit_logger()

        try:
            response = await call_next(request)
            return response
        except Exception as e:
            user_id = None
            if hasattr(request.state, "user_id"):
                user_id = request.state.user_id

            # Log error
            self.audit_logger.log_event(
                event_type=AuditEventType.API_ERROR,
                user_id=user_id,
                resource_type="api",
                resource_id=request.url.path,
                action=request.method,
                status="failure",
                severity=AuditSeverity.CRITICAL,
                context={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "ip": request.client.host if request.client else None,
                },
            )

            logger.error(
                f"Error processing request: {e}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "user_id": user_id,
                },
            )

            raise


class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking API performance."""

    # Thresholds (in seconds)
    SLOW_REQUEST_THRESHOLD = 1.0
    VERY_SLOW_REQUEST_THRESHOLD = 5.0

    def __init__(self, app):
        """Initialize middleware."""
        super().__init__(app)
        self.audit_logger = None

    async def dispatch(self, request: Request, call_next):
        """Process request and track performance."""
        if self.audit_logger is None:
            self.audit_logger = get_audit_logger()

        start_time = time.time()

        # Call next middleware/endpoint
        response = await call_next(request)

        duration = time.time() - start_time

        # Log if slow
        if duration > self.VERY_SLOW_REQUEST_THRESHOLD:
            severity = AuditSeverity.WARNING
            logger.warning(
                f"Very slow request: {request.method} {request.url.path} took {duration:.3f}s"
            )
        elif duration > self.SLOW_REQUEST_THRESHOLD:
            severity = AuditSeverity.INFO
            logger.info(
                f"Slow request: {request.method} {request.url.path} took {duration:.3f}s"
            )
        else:
            return response

        # Log performance event
        self.audit_logger.log_event(
            event_type=AuditEventType.SYSTEM_CONFIG_CHANGED,
            user_id=None,
            resource_type="performance",
            resource_id=request.url.path,
            action="request_processing",
            status="slow" if duration > self.SLOW_REQUEST_THRESHOLD else "normal",
            severity=severity,
            context={
                "method": request.method,
                "path": request.url.path,
                "duration": f"{duration:.3f}s",
                "status_code": response.status_code,
            },
        )

        return response
