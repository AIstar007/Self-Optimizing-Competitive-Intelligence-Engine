"""Tests for security infrastructure."""

import pytest
from datetime import datetime, timedelta
from typing import List

from core.infrastructure.security.rbac import (
    RBACManager,
    Role,
    User,
    Permission,
    RoleType,
)
from core.infrastructure.security.jwt_handler import JWTTokenHandler
from core.infrastructure.security.encryption import (
    EncryptionService,
    DataMaskingService,
    SecretsVault,
    SecureConfigManager,
)
from core.infrastructure.security.audit_logger import (
    AuditLogger,
    AuditEventType,
    AuditSeverity,
)
from core.infrastructure.security.compliance import (
    ComplianceManager,
    ComplianceFramework,
    DataClassification,
    UserConsent,
    ConsentType,
)


class TestRBAC:
    """Tests for RBAC."""

    def setup_method(self):
        """Setup test environment."""
        self.rbac = RBACManager()

    def test_create_role(self):
        """Test creating role."""
        role = self.rbac.create_role(
            role_id="test_role",
            name="Test Role",
            permissions=[Permission.DATA_READ, Permission.DATA_WRITE],
        )

        assert role.role_id == "test_role"
        assert role.name == "Test Role"
        assert Permission.DATA_READ in role.permissions
        assert Permission.DATA_WRITE in role.permissions

    def test_create_user(self):
        """Test creating user."""
        user = self.rbac.create_user(
            user_id="test_user",
            username="testuser",
            email="test@example.com",
        )

        assert user.user_id == "test_user"
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_assign_role_to_user(self):
        """Test assigning role to user."""
        user = self.rbac.create_user("user1", "user1", "user1@example.com")
        self.rbac.assign_role_to_user("user1", RoleType.ANALYST.value)

        retrieved_user = self.rbac.get_user("user1")
        assert RoleType.ANALYST.value in retrieved_user.roles

    def test_check_permission(self):
        """Test checking permission."""
        self.rbac.create_user("user1", "user1", "user1@example.com")
        self.rbac.assign_role_to_user("user1", RoleType.ADMIN.value)

        # Admin should have all permissions
        assert self.rbac.check_permission("user1", Permission.USER_MANAGE)

    def test_admin_has_all_permissions(self):
        """Test that admin has all permissions."""
        self.rbac.create_user("admin", "admin", "admin@example.com")
        self.rbac.assign_role_to_user("admin", RoleType.ADMIN.value)

        for permission in Permission:
            assert self.rbac.check_permission("admin", permission)

    def test_viewer_has_limited_permissions(self):
        """Test that viewer has limited permissions."""
        self.rbac.create_user("viewer", "viewer", "viewer@example.com")
        self.rbac.assign_role_to_user("viewer", RoleType.VIEWER.value)

        assert self.rbac.check_permission("viewer", Permission.DATA_READ)
        assert not self.rbac.check_permission("viewer", Permission.USER_MANAGE)

    def test_get_statistics(self):
        """Test getting statistics."""
        self.rbac.create_user("user1", "user1", "user1@example.com")
        self.rbac.create_user("user2", "user2", "user2@example.com")

        stats = self.rbac.get_statistics()
        assert stats["total_users"] == 2
        assert stats["total_roles"] >= 5  # At least default roles


class TestJWTHandler:
    """Tests for JWT token handler."""

    def setup_method(self):
        """Setup test environment."""
        self.token_handler = JWTTokenHandler()

    def test_generate_access_token(self):
        """Test generating access token."""
        token = self.token_handler.generate_access_token(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=["admin"],
            permissions=["read", "write"],
        )

        assert token is not None
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verifying valid token."""
        token = self.token_handler.generate_access_token(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=["admin"],
            permissions=["read"],
        )

        payload = self.token_handler.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "user1"
        assert payload["username"] == "testuser"

    def test_verify_invalid_token(self):
        """Test verifying invalid token."""
        payload = self.token_handler.verify_token("invalid_token")
        assert payload is None

    def test_token_refresh(self):
        """Test token refresh."""
        refresh_token = self.token_handler.generate_refresh_token("user1")
        assert refresh_token is not None

        # Should be valid initially
        payload = self.token_handler.verify_token(refresh_token)
        # Refresh token payload structure might be different, just check it's valid
        assert payload is not None

    def test_revoke_token(self):
        """Test token revocation."""
        token = self.token_handler.generate_access_token(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=["admin"],
            permissions=["read"],
        )

        # Verify it works initially
        assert self.token_handler.verify_token(token) is not None

        # Revoke it
        self.token_handler.revoke_token(token)

        # Should now be invalid
        assert not self.token_handler.is_token_valid(token)

    def test_get_statistics(self):
        """Test getting token statistics."""
        self.token_handler.generate_access_token(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=["admin"],
            permissions=["read"],
        )

        stats = self.token_handler.get_statistics()
        assert "total_issued" in stats
        assert stats["total_issued"] > 0


class TestEncryption:
    """Tests for encryption service."""

    def setup_method(self):
        """Setup test environment."""
        self.encryption = EncryptionService()
        self.masking = DataMaskingService()
        self.vault = SecretsVault()
        self.config = SecureConfigManager()

    def test_encrypt_decrypt(self):
        """Test encryption and decryption."""
        original = "test_data_123"
        encrypted = self.encryption.encrypt(original)

        assert encrypted != original
        assert self.encryption.is_encrypted(encrypted)

        decrypted = self.encryption.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_dict(self):
        """Test dictionary encryption."""
        data = {"username": "john", "email": "john@example.com", "age": 30}

        encrypted = self.encryption.encrypt_dict(data, fields=["username", "email"])
        decrypted = self.encryption.decrypt_dict(encrypted, fields=["username", "email"])

        assert decrypted["username"] == "john"
        assert decrypted["email"] == "john@example.com"
        assert decrypted["age"] == 30

    def test_mask_email(self):
        """Test email masking."""
        masked = self.masking.mask_email("john.doe@example.com")
        assert "john.doe" not in masked
        assert "*" in masked

    def test_mask_token(self):
        """Test token masking."""
        token = "super_secret_token_1234567890"
        masked = self.masking.mask_token(token)

        assert masked.startswith("super")
        assert "1234567890" not in masked
        assert "*" in masked

    def test_mask_phone(self):
        """Test phone masking."""
        masked = self.masking.mask_phone("1234567890")
        assert "1234" not in masked
        assert "7890" in masked

    def test_mask_credit_card(self):
        """Test credit card masking."""
        masked = self.masking.mask_credit_card("4532015112830366")
        assert "4532" not in masked
        assert "0366" in masked

    def test_secrets_vault(self):
        """Test secrets vault."""
        self.vault.store_secret("api_key", "super_secret_api_key_value")

        assert self.vault.secret_exists("api_key")

        retrieved = self.vault.retrieve_secret("api_key")
        assert retrieved == "super_secret_api_key_value"

        self.vault.delete_secret("api_key")
        assert not self.vault.secret_exists("api_key")

    def test_secure_config(self):
        """Test secure config manager."""
        self.config.set_config("database_url", "postgresql://localhost/db")
        self.config.set_config(
            "api_key", "secret_key_12345", encrypt=True
        )

        assert self.config.get_config("database_url") == "postgresql://localhost/db"
        assert self.config.get_config("api_key") == "secret_key_12345"


class TestAuditLogger:
    """Tests for audit logger."""

    def setup_method(self):
        """Setup test environment."""
        self.audit = AuditLogger()

    def test_log_event(self):
        """Test logging event."""
        self.audit.log_event(
            event_type=AuditEventType.LOGIN,
            user_id="user1",
            resource_type="authentication",
            action="login",
            status="success",
        )

        assert len(self.audit.events) > 0

    def test_log_authentication(self):
        """Test logging authentication."""
        self.audit.log_authentication("user1", True)
        self.audit.log_authentication("user2", False)

        assert len(self.audit.events) == 2

    def test_get_events_by_user(self):
        """Test getting events by user."""
        self.audit.log_event(
            event_type=AuditEventType.LOGIN,
            user_id="user1",
            resource_type="authentication",
            action="login",
            status="success",
        )
        self.audit.log_event(
            event_type=AuditEventType.DATA_READ,
            user_id="user2",
            resource_type="data",
            action="read",
            status="success",
        )

        user1_events = self.audit.get_events_by_user("user1")
        assert len(user1_events) == 1
        assert user1_events[0].user_id == "user1"

    def test_get_critical_events(self):
        """Test getting critical events."""
        self.audit.log_event(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            user_id="user1",
            resource_type="security",
            action="unauthorized_access",
            status="failure",
            severity=AuditSeverity.CRITICAL,
        )

        critical = self.audit.get_critical_events()
        assert len(critical) > 0

    def test_export_events(self):
        """Test exporting events."""
        self.audit.log_event(
            event_type=AuditEventType.LOGIN,
            user_id="user1",
            resource_type="authentication",
            action="login",
            status="success",
        )

        exported = self.audit.export_events()
        assert isinstance(exported, str)
        assert "user1" in exported

    def test_get_statistics(self):
        """Test getting statistics."""
        self.audit.log_event(
            event_type=AuditEventType.LOGIN,
            user_id="user1",
            resource_type="authentication",
            action="login",
            status="success",
        )

        stats = self.audit.get_statistics()
        assert stats["total_events"] > 0


class TestCompliance:
    """Tests for compliance."""

    def setup_method(self):
        """Setup test environment."""
        self.compliance = ComplianceManager()

    def test_register_gdpr_compliance(self):
        """Test registering GDPR compliance."""
        self.compliance.register_gdpr_compliance(
            name="Our GDPR Program",
            dpia_completed=True,
            scc_in_place=True,
            dpa_signed=True,
        )

        status = self.compliance.get_compliance_status()
        assert ComplianceFramework.GDPR.value in status["frameworks"]

    def test_add_retention_policy(self):
        """Test adding retention policy."""
        self.compliance.add_retention_policy(
            name="Customer Data",
            days_to_retain=365,
            data_types=["emails", "transactions"],
        )

        # Policy should be registered
        stats = self.compliance.get_statistics()
        assert stats["total_retention_policies"] > 0

    def test_record_user_consent(self):
        """Test recording user consent."""
        self.compliance.record_consent(
            user_id="user1",
            consent_type=ConsentType.DATA_PROCESSING,
            granted=True,
            expires_in_days=365,
        )

        consents = self.compliance.get_user_consents("user1")
        assert len(consents) > 0
        assert consents[0].granted is True

    def test_check_user_consent(self):
        """Test checking user consent."""
        self.compliance.record_consent(
            user_id="user1",
            consent_type=ConsentType.DATA_PROCESSING,
            granted=True,
            expires_in_days=365,
        )

        has_consent = self.compliance.check_user_consent(
            "user1", ConsentType.DATA_PROCESSING
        )
        assert has_consent is True

    def test_get_compliance_status(self):
        """Test getting compliance status."""
        self.compliance.register_gdpr_compliance(
            name="GDPR Program",
            dpia_completed=True,
            scc_in_place=True,
            dpa_signed=True,
        )

        status = self.compliance.get_compliance_status()
        assert "frameworks" in status
        assert "requirements" in status
        assert "overall_percentage" in status


class TestIntegration:
    """Integration tests."""

    def setup_method(self):
        """Setup test environment."""
        self.rbac = RBACManager()
        self.token_handler = JWTTokenHandler()
        self.audit = AuditLogger()
        self.encryption = EncryptionService()

    def test_full_authentication_flow(self):
        """Test full authentication flow."""
        # Create user
        user = self.rbac.create_user("user1", "testuser", "test@example.com")
        self.rbac.assign_role_to_user("user1", RoleType.ANALYST.value)

        # Log login
        self.audit.log_authentication("user1", True)

        # Generate token
        permissions = [p.value for p in self.rbac.get_user_permissions("user1")]
        token = self.token_handler.generate_access_token(
            user_id="user1",
            username="testuser",
            email="test@example.com",
            roles=[RoleType.ANALYST.value],
            permissions=permissions,
        )

        # Verify token
        payload = self.token_handler.verify_token(token)
        assert payload["user_id"] == "user1"

    def test_secure_data_handling(self):
        """Test secure data handling."""
        # Create user with encrypted email
        user_data = {
            "username": "john",
            "email": "john@example.com",
            "password_hash": "hashed_password_123",
        }

        # Encrypt sensitive fields
        encrypted = self.encryption.encrypt_dict(
            user_data, fields=["email", "password_hash"]
        )

        # Verify encryption
        assert self.encryption.is_encrypted(encrypted["email"])

        # Decrypt
        decrypted = self.encryption.decrypt_dict(
            encrypted, fields=["email", "password_hash"]
        )
        assert decrypted["email"] == "john@example.com"

        # Log data access
        self.audit.log_data_access("user1", "user_data", "read", True)

        events = self.audit.get_events_by_user("user1")
        assert any(e.event_type == AuditEventType.DATA_READ for e in events)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
