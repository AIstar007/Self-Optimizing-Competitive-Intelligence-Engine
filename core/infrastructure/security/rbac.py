"""Role-Based Access Control (RBAC) framework."""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class Permission(Enum):
    """System permissions."""

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"

    # Role management
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_LIST = "role:list"

    # Data access
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_DELETE = "data:delete"
    DATA_EXPORT = "data:export"

    # Intelligence operations
    ANALYSIS_CREATE = "analysis:create"
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_UPDATE = "analysis:update"
    ANALYSIS_DELETE = "analysis:delete"

    # Reporting
    REPORT_CREATE = "report:create"
    REPORT_READ = "report:read"
    REPORT_UPDATE = "report:update"
    REPORT_DELETE = "report:delete"
    REPORT_PUBLISH = "report:publish"

    # Integrations
    INTEGRATION_CREATE = "integration:create"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_UPDATE = "integration:update"
    INTEGRATION_DELETE = "integration:delete"
    INTEGRATION_MANAGE = "integration:manage"

    # Settings & Configuration
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"
    SETTINGS_MANAGE = "settings:manage"

    # Audit & Security
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    SECURITY_MANAGE = "security:manage"

    # Admin operations
    ADMIN = "admin"


class RoleType(Enum):
    """Predefined system roles."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    DATA_MANAGER = "data_manager"
    INTEGRATION_MANAGER = "integration_manager"
    CUSTOM = "custom"


@dataclass
class Role:
    """Role definition with permissions."""

    role_id: str
    name: str
    role_type: RoleType
    permissions: Set[Permission] = field(default_factory=set)
    description: Optional[str] = None
    is_system_role: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has permission."""
        return permission in self.permissions

    def grant_permission(self, permission: Permission) -> None:
        """Grant permission to role."""
        self.permissions.add(permission)
        self.updated_at = datetime.utcnow()
        logger.debug(f"Granted {permission.value} to role {self.name}")

    def revoke_permission(self, permission: Permission) -> None:
        """Revoke permission from role."""
        self.permissions.discard(permission)
        self.updated_at = datetime.utcnow()
        logger.debug(f"Revoked {permission.value} from role {self.name}")

    def grant_permissions(self, permissions: List[Permission]) -> None:
        """Grant multiple permissions."""
        for permission in permissions:
            self.grant_permission(permission)

    def revoke_all_permissions(self) -> None:
        """Revoke all permissions."""
        self.permissions.clear()
        self.updated_at = datetime.utcnow()


@dataclass
class User:
    """User with roles."""

    user_id: str
    username: str
    email: str
    roles: Set[str] = field(default_factory=set)  # role_ids
    is_active: bool = True
    is_system_user: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    def assign_role(self, role_id: str) -> None:
        """Assign role to user."""
        self.roles.add(role_id)
        self.updated_at = datetime.utcnow()

    def remove_role(self, role_id: str) -> None:
        """Remove role from user."""
        self.roles.discard(role_id)
        self.updated_at = datetime.utcnow()

    def has_role(self, role_id: str) -> bool:
        """Check if user has role."""
        return role_id in self.roles

    def clear_roles(self) -> None:
        """Remove all roles from user."""
        self.roles.clear()
        self.updated_at = datetime.utcnow()


class RBACManager:
    """Role-based access control manager."""

    def __init__(self):
        """Initialize RBAC manager."""
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self) -> None:
        """Initialize default system roles."""
        # Admin role - all permissions
        admin_role = Role(
            role_id="role_admin",
            name="Administrator",
            role_type=RoleType.ADMIN,
            description="Full system access",
            is_system_role=True,
        )
        admin_role.grant_permissions(list(Permission))
        self.roles["role_admin"] = admin_role

        # Analyst role - read and analysis permissions
        analyst_role = Role(
            role_id="role_analyst",
            name="Analyst",
            role_type=RoleType.ANALYST,
            description="Can view data and perform analysis",
            is_system_role=True,
        )
        analyst_permissions = [
            Permission.DATA_READ,
            Permission.ANALYSIS_CREATE,
            Permission.ANALYSIS_READ,
            Permission.ANALYSIS_UPDATE,
            Permission.REPORT_READ,
            Permission.USER_READ,
            Permission.ROLE_LIST,
            Permission.AUDIT_READ,
        ]
        analyst_role.grant_permissions(analyst_permissions)
        self.roles["role_analyst"] = analyst_role

        # Viewer role - read-only
        viewer_role = Role(
            role_id="role_viewer",
            name="Viewer",
            role_type=RoleType.VIEWER,
            description="Read-only access to reports and data",
            is_system_role=True,
        )
        viewer_permissions = [
            Permission.DATA_READ,
            Permission.ANALYSIS_READ,
            Permission.REPORT_READ,
            Permission.USER_READ,
        ]
        viewer_role.grant_permissions(viewer_permissions)
        self.roles["role_viewer"] = viewer_role

        # Data Manager role
        data_manager_role = Role(
            role_id="role_data_manager",
            name="Data Manager",
            role_type=RoleType.DATA_MANAGER,
            description="Can manage data lifecycle",
            is_system_role=True,
        )
        data_manager_permissions = [
            Permission.DATA_READ,
            Permission.DATA_WRITE,
            Permission.DATA_DELETE,
            Permission.DATA_EXPORT,
            Permission.ANALYSIS_READ,
            Permission.REPORT_READ,
            Permission.AUDIT_READ,
        ]
        data_manager_role.grant_permissions(data_manager_permissions)
        self.roles["role_data_manager"] = data_manager_role

        # Integration Manager role
        integration_manager_role = Role(
            role_id="role_integration_manager",
            name="Integration Manager",
            role_type=RoleType.INTEGRATION_MANAGER,
            description="Can manage integrations and webhooks",
            is_system_role=True,
        )
        integration_permissions = [
            Permission.INTEGRATION_CREATE,
            Permission.INTEGRATION_READ,
            Permission.INTEGRATION_UPDATE,
            Permission.INTEGRATION_DELETE,
            Permission.INTEGRATION_MANAGE,
            Permission.SETTINGS_READ,
            Permission.AUDIT_READ,
        ]
        integration_manager_role.grant_permissions(integration_permissions)
        self.roles["role_integration_manager"] = integration_manager_role

        logger.info("Initialized 5 default system roles")

    def create_role(
        self,
        role_id: str,
        name: str,
        permissions: Optional[List[Permission]] = None,
        description: Optional[str] = None,
    ) -> Role:
        """Create custom role."""
        if role_id in self.roles:
            raise ValueError(f"Role {role_id} already exists")

        role = Role(
            role_id=role_id,
            name=name,
            role_type=RoleType.CUSTOM,
            description=description,
            is_system_role=False,
        )

        if permissions:
            role.grant_permissions(permissions)

        self.roles[role_id] = role
        logger.info(f"Created role {name} ({role_id})")
        return role

    def delete_role(self, role_id: str) -> bool:
        """Delete custom role."""
        if role_id not in self.roles:
            return False

        role = self.roles[role_id]
        if role.is_system_role:
            logger.warning(f"Cannot delete system role {role_id}")
            return False

        # Unassign from all users
        for user in self.users.values():
            if user.has_role(role_id):
                user.remove_role(role_id)

        del self.roles[role_id]
        logger.info(f"Deleted role {role_id}")
        return True

    def get_role(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        return self.roles.get(role_id)

    def list_roles(self, include_system: bool = True) -> List[Role]:
        """List all roles."""
        roles = list(self.roles.values())

        if not include_system:
            roles = [r for r in roles if not r.is_system_role]

        return sorted(roles, key=lambda r: r.name)

    def create_user(self, user_id: str, username: str, email: str) -> User:
        """Create user."""
        if user_id in self.users:
            raise ValueError(f"User {user_id} already exists")

        user = User(user_id=user_id, username=username, email=email)
        self.users[user_id] = user
        logger.info(f"Created user {username} ({user_id})")
        return user

    def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        if user_id not in self.users:
            return False

        user = self.users[user_id]
        if user.is_system_user:
            logger.warning(f"Cannot delete system user {user_id}")
            return False

        del self.users[user_id]
        logger.info(f"Deleted user {user_id}")
        return True

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def list_users(self, active_only: bool = True) -> List[User]:
        """List all users."""
        users = list(self.users.values())

        if active_only:
            users = [u for u in users if u.is_active]

        return sorted(users, key=lambda u: u.username)

    def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Assign role to user."""
        if user_id not in self.users or role_id not in self.roles:
            return False

        user = self.users[user_id]
        user.assign_role(role_id)
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return True

    def remove_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Remove role from user."""
        if user_id not in self.users:
            return False

        user = self.users[user_id]
        user.remove_role(role_id)
        logger.info(f"Removed role {role_id} from user {user_id}")
        return True

    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has permission."""
        if user_id not in self.users:
            return False

        user = self.users[user_id]

        if not user.is_active:
            return False

        # Check admin shortcut
        for role_id in user.roles:
            if role_id not in self.roles:
                continue

            role = self.roles[role_id]
            if Permission.ADMIN in role.permissions:
                return True

        # Check specific permission
        for role_id in user.roles:
            if role_id not in self.roles:
                continue

            role = self.roles[role_id]
            if role.has_permission(permission):
                return True

        return False

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for user."""
        permissions = set()

        if user_id not in self.users:
            return permissions

        user = self.users[user_id]

        for role_id in user.roles:
            if role_id not in self.roles:
                continue

            role = self.roles[role_id]
            permissions.update(role.permissions)

        return permissions

    def get_role_permissions(self, role_id: str) -> Set[Permission]:
        """Get all permissions for role."""
        if role_id not in self.roles:
            return set()

        return self.roles[role_id].permissions.copy()

    def get_statistics(self) -> Dict:
        """Get RBAC statistics."""
        active_users = sum(1 for u in self.users.values() if u.is_active)
        system_roles = sum(1 for r in self.roles.values() if r.is_system_role)
        custom_roles = sum(1 for r in self.roles.values() if not r.is_system_role)

        return {
            "total_users": len(self.users),
            "active_users": active_users,
            "total_roles": len(self.roles),
            "system_roles": system_roles,
            "custom_roles": custom_roles,
            "total_permissions": len(Permission),
        }


# Global instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get or create global RBAC manager."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager
