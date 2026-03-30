"""Security API router for authentication, authorization, and compliance."""

import logging
from typing import List, Optional
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, Body, Query
from pydantic import BaseModel, Field

from core.infrastructure.security.rbac import (
    get_rbac_manager,
    RBACManager,
    Permission,
    RoleType,
)
from core.infrastructure.security.jwt_handler import (
    get_token_handler,
    JWTTokenHandler,
)
from core.infrastructure.security.audit_logger import (
    get_audit_logger,
    AuditLogger,
    AuditEventType,
    AuditSeverity,
)
from core.infrastructure.security.encryption import (
    get_encryption_service,
    get_config_manager,
)
from core.infrastructure.security.compliance import (
    get_compliance_manager,
    ComplianceFramework,
    ComplianceManager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/security", tags=["security"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RoleRequest(BaseModel):
    """Create/update role request."""

    name: str = Field(..., description="Role name")
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class RoleResponse(BaseModel):
    """Role response."""

    role_id: str
    name: str
    role_type: str
    permissions: List[str]
    is_system_role: bool


class UserRequest(BaseModel):
    """Create/update user request."""

    username: str
    email: str
    roles: List[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    """User response."""

    user_id: str
    username: str
    email: str
    roles: List[str]
    is_active: bool


class PermissionCheckRequest(BaseModel):
    """Permission check request."""

    user_id: str
    permission: str


class AuditEventResponse(BaseModel):
    """Audit event response."""

    event_type: str
    user_id: Optional[str]
    timestamp: str
    resource_type: str
    action: str
    status: str
    severity: str


class ComplianceStatusResponse(BaseModel):
    """Compliance status response."""

    frameworks: dict
    requirements: dict
    overall_percentage: float


# Authentication Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    rbac_manager: RBACManager = Depends(get_rbac_manager),
    token_handler: JWTTokenHandler = Depends(get_token_handler),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Login user and get tokens."""
    try:
        # Find user
        user = None
        for u in rbac_manager.list_users(active_only=True):
            if u.username == request.username:
                user = u
                break

        if not user:
            audit_logger.log_authentication(request.username, False)
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # In production, verify password hash
        # This is a simplified example
        audit_logger.log_authentication(user.user_id, True)

        # Get user roles and permissions
        roles = list(user.roles)
        permissions = [
            p.value for p in rbac_manager.get_user_permissions(user.user_id)
        ]

        # Generate tokens
        access_token = token_handler.generate_access_token(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            roles=roles,
            permissions=permissions,
        )

        refresh_token = token_handler.generate_refresh_token(user.user_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": token_handler.access_token_expire_minutes * 60,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/logout")
async def logout(
    token: str = Body(..., description="Token to revoke"),
    token_handler: JWTTokenHandler = Depends(get_token_handler),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Logout user and revoke token."""
    try:
        payload = token_handler.verify_token(token)
        if payload:
            user_id = payload.get("user_id")
            token_handler.revoke_token(token)
            audit_logger.log_event(
                AuditEventType.LOGOUT,
                user_id=user_id,
                resource_type="authentication",
                action="logout",
                status="success",
            )
            return {"message": "Logged out successfully"}

        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


# RBAC Management Endpoints
@router.post("/roles", response_model=RoleResponse)
async def create_role(
    request: RoleRequest,
    rbac_manager: RBACManager = Depends(get_rbac_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Create new role."""
    try:
        permissions = [Permission[p.upper()] for p in request.permissions]
        role = rbac_manager.create_role(
            role_id=f"role_{request.name.lower().replace(' ', '_')}",
            name=request.name,
            permissions=permissions,
            description=request.description,
        )

        audit_logger.log_event(
            AuditEventType.ROLE_CREATED,
            user_id="system",
            resource_type="role",
            resource_id=role.role_id,
            action="create",
            status="success",
        )

        return {
            "role_id": role.role_id,
            "name": role.name,
            "role_type": role.role_type.value,
            "permissions": [p.value for p in role.permissions],
            "is_system_role": role.is_system_role,
        }
    except Exception as e:
        logger.error(f"Error creating role: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    include_system: bool = Query(True),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> list:
    """List all roles."""
    try:
        roles = rbac_manager.list_roles(include_system=include_system)
        return [
            {
                "role_id": r.role_id,
                "name": r.name,
                "role_type": r.role_type.value,
                "permissions": [p.value for p in r.permissions],
                "is_system_role": r.is_system_role,
            }
            for r in roles
        ]
    except Exception as e:
        logger.error(f"Error listing roles: {e}")
        raise HTTPException(status_code=500, detail="Failed to list roles")


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    active_only: bool = Query(True),
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> list:
    """List all users."""
    try:
        users = rbac_manager.list_users(active_only=active_only)
        return [
            {
                "user_id": u.user_id,
                "username": u.username,
                "email": u.email,
                "roles": list(u.roles),
                "is_active": u.is_active,
            }
            for u in users
        ]
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserRequest,
    rbac_manager: RBACManager = Depends(get_rbac_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Create new user."""
    try:
        user = rbac_manager.create_user(
            user_id=f"user_{request.username}",
            username=request.username,
            email=request.email,
        )

        # Assign roles
        for role_id in request.roles:
            rbac_manager.assign_role_to_user(user.user_id, role_id)

        audit_logger.log_user_action(
            actor_id="system",
            user_id=user.user_id,
            action="create",
            success=True,
        )

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "roles": list(user.roles),
            "is_active": user.is_active,
        }
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/permissions/check")
async def check_permission(
    request: PermissionCheckRequest,
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> dict:
    """Check if user has permission."""
    try:
        permission = Permission[request.permission.upper()]
        has_permission = rbac_manager.check_permission(request.user_id, permission)

        return {
            "user_id": request.user_id,
            "permission": permission.value,
            "has_permission": has_permission,
        }
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# Audit Endpoints
@router.get("/audit/events", response_model=List[AuditEventResponse])
async def get_audit_events(
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> list:
    """Get audit events."""
    try:
        if user_id:
            events = audit_logger.get_events_by_user(user_id, limit=limit)
        else:
            events = audit_logger.events[-limit :]

        return [
            {
                "event_type": e.event_type.value,
                "user_id": e.user_id,
                "timestamp": e.timestamp.isoformat(),
                "resource_type": e.resource_type,
                "action": e.action,
                "status": e.status,
                "severity": e.severity.value,
            }
            for e in events
        ]
    except Exception as e:
        logger.error(f"Error getting audit events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit events")


@router.get("/audit/statistics")
async def get_audit_statistics(
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Get audit statistics."""
    try:
        return audit_logger.get_statistics()
    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit statistics")


# Compliance Endpoints
@router.get("/compliance/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    compliance_manager: ComplianceManager = Depends(get_compliance_manager),
) -> dict:
    """Get compliance status."""
    try:
        return compliance_manager.get_compliance_status()
    except Exception as e:
        logger.error(f"Error getting compliance status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get compliance status")


@router.get("/rbac/statistics")
async def get_rbac_statistics(
    rbac_manager: RBACManager = Depends(get_rbac_manager),
) -> dict:
    """Get RBAC statistics."""
    try:
        return rbac_manager.get_statistics()
    except Exception as e:
        logger.error(f"Error getting RBAC stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get RBAC statistics")


@router.get("/tokens/statistics")
async def get_token_statistics(
    token_handler: JWTTokenHandler = Depends(get_token_handler),
) -> dict:
    """Get token statistics."""
    try:
        return token_handler.get_statistics()
    except Exception as e:
        logger.error(f"Error getting token stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get token statistics")
