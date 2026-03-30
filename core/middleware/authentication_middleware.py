"""Authentication middleware for JWT verification and permission checking."""

import logging
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware

from core.infrastructure.security.jwt_handler import get_token_handler, JWTTokenHandler
from core.infrastructure.security.rbac import get_rbac_manager, RBACManager, Permission
from core.infrastructure.security.audit_logger import (
    get_audit_logger,
    AuditLogger,
    AuditEventType,
)

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication and verification."""

    def __init__(self, app):
        """Initialize middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        # Skip auth for public endpoints
        public_paths = ["/api/v1/security/login", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return self._unauthorized_response("Missing authorization header")

        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return self._unauthorized_response("Invalid authorization scheme")
        except ValueError:
            return self._unauthorized_response("Invalid authorization header")

        # Verify token
        token_handler = get_token_handler()
        payload = token_handler.verify_token(token)

        if not payload:
            audit_logger = get_audit_logger()
            audit_logger.log_event(
                AuditEventType.AUTHENTICATION_FAILED,
                user_id=None,
                resource_type="authentication",
                action="token_verification",
                status="failure",
                context={"ip": request.client.host if request.client else None},
            )
            return self._unauthorized_response("Invalid or expired token")

        # Attach user info to request state
        request.state.user_id = payload.get("user_id")
        request.state.username = payload.get("username")
        request.state.email = payload.get("email")
        request.state.roles = payload.get("roles", [])
        request.state.permissions = payload.get("permissions", [])

        response = await call_next(request)
        return response

    @staticmethod
    def _unauthorized_response(message: str):
        """Return unauthorized response."""
        return HTTPException(status_code=401, detail=message)


class PermissionCheckMiddleware(BaseHTTPMiddleware):
    """Middleware for permission-based access control."""

    # Endpoint to required permission mapping
    ENDPOINT_PERMISSIONS = {
        "POST /api/v1/security/roles": Permission.ROLE_MANAGE,
        "DELETE /api/v1/security/roles": Permission.ROLE_MANAGE,
        "POST /api/v1/security/users": Permission.USER_MANAGE,
        "DELETE /api/v1/security/users": Permission.USER_MANAGE,
        "GET /api/v1/audit/events": Permission.AUDIT_READ,
        "GET /api/v1/compliance/status": Permission.COMPLIANCE_READ,
    }

    async def dispatch(self, request: Request, call_next):
        """Process request."""
        # Skip permission check for public endpoints
        if not hasattr(request.state, "user_id"):
            return await call_next(request)

        # Check if endpoint requires permission
        endpoint_key = f"{request.method} {request.url.path}"
        required_permission = None

        for pattern, perm in self.ENDPOINT_PERMISSIONS.items():
            if self._match_endpoint(endpoint_key, pattern):
                required_permission = perm
                break

        if required_permission:
            # Check permission
            user_permissions = request.state.permissions or []
            if required_permission.value not in user_permissions:
                audit_logger = get_audit_logger()
                audit_logger.log_event(
                    AuditEventType.PERMISSION_DENIED,
                    user_id=request.state.user_id,
                    resource_type="authorization",
                    action=request.method,
                    status="failure",
                    context={
                        "endpoint": endpoint_key,
                        "required_permission": required_permission.value,
                    },
                )
                return HTTPException(status_code=403, detail="Insufficient permissions")

        response = await call_next(request)
        return response

    @staticmethod
    def _match_endpoint(endpoint: str, pattern: str) -> bool:
        """Match endpoint against pattern."""
        # Simple pattern matching for basic cases
        parts = pattern.split()
        if len(parts) != 2:
            return False

        method, path = parts
        endpoint_method, endpoint_path = endpoint.split(" ", 1)

        return (
            method == endpoint_method or method == "*"
        ) and endpoint_path.startswith(path)


async def get_current_user(request: Request) -> dict:
    """Get current user from request."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user_id": request.state.user_id,
        "username": request.state.username,
        "email": request.state.email,
        "roles": request.state.roles,
        "permissions": request.state.permissions,
    }


async def require_permission(permission: Permission):
    """Dependency for requiring specific permission."""

    async def check(request: Request):
        if not hasattr(request.state, "user_id"):
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_permissions = request.state.permissions or []
        if permission.value not in user_permissions:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        return request.state.user_id

    return check


async def require_role(role_name: str):
    """Dependency for requiring specific role."""

    async def check(request: Request):
        if not hasattr(request.state, "user_id"):
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_roles = request.state.roles or []
        if role_name not in user_roles:
            raise HTTPException(status_code=403, detail="Insufficient role")

        return request.state.user_id

    return check


def authenticate_user(func: Callable) -> Callable:
    """Decorator for authenticating user on function."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request") or (args[0] if args else None)
        if not isinstance(request, Request):
            return await func(*args, **kwargs)

        if not hasattr(request.state, "user_id"):
            raise HTTPException(status_code=401, detail="Not authenticated")

        return await func(*args, **kwargs)

    return wrapper


def check_permission(required_permission: Permission):
    """Decorator for checking permission on function."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            if not isinstance(request, Request):
                return await func(*args, **kwargs)

            if not hasattr(request.state, "user_id"):
                raise HTTPException(status_code=401, detail="Not authenticated")

            user_permissions = request.state.permissions or []
            if required_permission.value not in user_permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def check_role(required_role: str):
    """Decorator for checking role on function."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or (args[0] if args else None)
            if not isinstance(request, Request):
                return await func(*args, **kwargs)

            if not hasattr(request.state, "user_id"):
                raise HTTPException(status_code=401, detail="Not authenticated")

            user_roles = request.state.roles or []
            if required_role not in user_roles:
                raise HTTPException(status_code=403, detail="Insufficient role")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class SecurityContext:
    """Context manager for security operations."""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list,
        permissions: list,
    ):
        """Initialize context."""
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has permission."""
        return permission.value in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has role."""
        return role in self.roles

    def has_any_permission(self, permissions: list) -> bool:
        """Check if user has any of the permissions."""
        return any(p.value in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: list) -> bool:
        """Check if user has all permissions."""
        return all(p.value in self.permissions for p in permissions)
