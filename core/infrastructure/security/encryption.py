"""Field-level encryption and data protection service."""

import logging
import os
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import secrets

logger = logging.getLogger(__name__)


class EncryptionService:
    """Encryption service for sensitive data."""

    def __init__(self, master_key: Optional[str] = None):
        """Initialize encryption service."""
        if master_key:
            self.master_key = master_key.encode()
        else:
            # Generate from environment or create new
            env_key = os.getenv("ENCRYPTION_KEY")
            if env_key:
                self.master_key = env_key.encode()
            else:
                self.master_key = Fernet.generate_key()

        self.cipher_suite = Fernet(self.master_key)
        self.encrypted_fields: Dict[str, str] = {}  # Track encrypted fields

    def encrypt(self, data: Any) -> str:
        """Encrypt data."""
        try:
            # Convert to string if needed
            if not isinstance(data, str):
                data = str(data)

            message = data.encode()
            encrypted = self.cipher_suite.encrypt(message)
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        try:
            encrypted = base64.b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(encrypted)
            return decrypted.decode()
        except InvalidToken:
            logger.error("Invalid encryption token - data may be corrupted")
            raise
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise

    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """Encrypt specific fields in dictionary."""
        encrypted_data = data.copy()

        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field] is not None:
                try:
                    encrypted_data[field] = self.encrypt(encrypted_data[field])
                    self.encrypted_fields[field] = "encrypted"
                except Exception as e:
                    logger.error(f"Error encrypting field {field}: {e}")
                    raise

        return encrypted_data

    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """Decrypt specific fields in dictionary."""
        decrypted_data = data.copy()

        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field] is not None:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception as e:
                    logger.error(f"Error decrypting field {field}: {e}")
                    raise

        return decrypted_data

    def is_encrypted(self, data: str) -> bool:
        """Check if data is encrypted."""
        try:
            # Try to decrypt to verify it's encrypted
            base64.b64decode(data.encode())
            return True
        except Exception:
            return False


class DataMaskingService:
    """Data masking for logs and displays."""

    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address."""
        if "@" not in email:
            return "***"
        parts = email.split("@")
        local = parts[0]
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{parts[1]}"

    @staticmethod
    def mask_token(token: str, visible_chars: int = 4) -> str:
        """Mask token/API key."""
        if len(token) <= visible_chars:
            return "*" * len(token)
        return token[:visible_chars] + "*" * (len(token) - visible_chars)

    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number."""
        if len(phone) <= 4:
            return "*" * len(phone)
        return "*" * (len(phone) - 4) + phone[-4:]

    @staticmethod
    def mask_credit_card(card: str) -> str:
        """Mask credit card number."""
        if len(card) <= 4:
            return "*" * len(card)
        return "*" * (len(card) - 4) + card[-4:]

    @staticmethod
    def mask_dict(data: Dict[str, Any], sensitive_fields: list) -> Dict[str, Any]:
        """Mask sensitive fields in dictionary."""
        masked = data.copy()

        for field in sensitive_fields:
            if field in masked:
                value = masked[field]
                if isinstance(value, str):
                    if "@" in value:  # Likely email
                        masked[field] = DataMaskingService.mask_email(value)
                    else:  # Likely token or API key
                        masked[field] = DataMaskingService.mask_token(value)
                else:
                    masked[field] = "***"

        return masked


class SecretsVault:
    """Secure secrets storage and retrieval."""

    def __init__(self):
        """Initialize secrets vault."""
        self.secrets: Dict[str, str] = {}
        self.encryption_service = EncryptionService()

    def store_secret(self, key: str, value: str) -> None:
        """Store encrypted secret."""
        try:
            encrypted = self.encryption_service.encrypt(value)
            self.secrets[key] = encrypted
            logger.debug(f"Stored secret {key}")
        except Exception as e:
            logger.error(f"Error storing secret: {e}")
            raise

    def retrieve_secret(self, key: str) -> Optional[str]:
        """Retrieve and decrypt secret."""
        if key not in self.secrets:
            logger.warning(f"Secret {key} not found")
            return None

        try:
            return self.encryption_service.decrypt(self.secrets[key])
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            return None

    def delete_secret(self, key: str) -> bool:
        """Delete secret."""
        if key in self.secrets:
            del self.secrets[key]
            logger.info(f"Deleted secret {key}")
            return True
        return False

    def secret_exists(self, key: str) -> bool:
        """Check if secret exists."""
        return key in self.secrets

    def list_secret_keys(self) -> list:
        """List all secret keys."""
        return list(self.secrets.keys())

    def clear_all(self) -> None:
        """Clear all secrets."""
        self.secrets.clear()
        logger.warning("Cleared all secrets from vault")


class SecureConfigManager:
    """Manage secure configuration."""

    def __init__(self):
        """Initialize config manager."""
        self.vault = SecretsVault()
        self.config: Dict[str, Any] = {}

    def set_config(self, key: str, value: Any, encrypt: bool = False) -> None:
        """Set configuration value."""
        if encrypt and isinstance(value, str):
            self.vault.store_secret(key, value)
        else:
            self.config[key] = value

        logger.debug(f"Set config {key}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        # Check vault first
        if self.vault.secret_exists(key):
            return self.vault.retrieve_secret(key)

        # Check config
        return self.config.get(key, default)

    def load_from_env(self, prefix: str = "APP_") -> None:
        """Load configuration from environment variables."""
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self.config[config_key] = value
                logger.debug(f"Loaded config {config_key} from environment")

    def load_from_dict(self, data: Dict[str, Any], encrypt_keys: list = None) -> None:
        """Load configuration from dictionary."""
        for key, value in data.items():
            if encrypt_keys and key in encrypt_keys:
                if isinstance(value, str):
                    self.vault.store_secret(key, value)
            else:
                self.config[key] = value

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration to dictionary."""
        result = self.config.copy()

        if include_secrets:
            for key in self.vault.list_secret_keys():
                result[key] = self.vault.retrieve_secret(key)

        return result

    def get_statistics(self) -> Dict:
        """Get config statistics."""
        return {
            "total_config_items": len(self.config),
            "total_secrets": len(self.vault.list_secret_keys()),
            "total_secure_items": len(self.config) + len(self.vault.list_secret_keys()),
        }


# Global instances
_encryption_service: Optional[EncryptionService] = None
_secrets_vault: Optional[SecretsVault] = None
_config_manager: Optional[SecureConfigManager] = None


def get_encryption_service() -> EncryptionService:
    """Get or create global encryption service."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def get_secrets_vault() -> SecretsVault:
    """Get or create global secrets vault."""
    global _secrets_vault
    if _secrets_vault is None:
        _secrets_vault = SecretsVault()
    return _secrets_vault


def get_config_manager() -> SecureConfigManager:
    """Get or create global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager
