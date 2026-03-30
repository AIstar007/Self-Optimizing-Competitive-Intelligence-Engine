"""Security module initialization."""

from core.infrastructure.security.rbac import (
    RBACManager,
    Role,
    User,
    Permission,
    RoleType,
    get_rbac_manager,
)
from core.infrastructure.security.jwt_handler import (
    JWTTokenHandler,
    TokenPayload,
    get_token_handler,
)
from core.infrastructure.security.encryption import (
    EncryptionService,
    DataMaskingService,
    SecretsVault,
    SecureConfigManager,
    get_encryption_service,
    get_secrets_vault,
    get_config_manager,
)
from core.infrastructure.security.audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    get_audit_logger,
)
from core.infrastructure.security.compliance import (
    ComplianceManager,
    ComplianceFramework,
    DataClassification,
    ConsentType,
    GDPRCompliance,
    SOC2Compliance,
    DataRetentionPolicy,
    UserConsent,
    PrivacyValidator,
    get_compliance_manager,
)

__all__ = [
    # RBAC
    "RBACManager",
    "Role",
    "User",
    "Permission",
    "RoleType",
    "get_rbac_manager",
    # JWT
    "JWTTokenHandler",
    "TokenPayload",
    "get_token_handler",
    # Encryption
    "EncryptionService",
    "DataMaskingService",
    "SecretsVault",
    "SecureConfigManager",
    "get_encryption_service",
    "get_secrets_vault",
    "get_config_manager",
    # Audit
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "get_audit_logger",
    # Compliance
    "ComplianceManager",
    "ComplianceFramework",
    "DataClassification",
    "ConsentType",
    "GDPRCompliance",
    "SOC2Compliance",
    "DataRetentionPolicy",
    "UserConsent",
    "PrivacyValidator",
    "get_compliance_manager",
]
