"""Deployment configuration management.

Provides environment-based configuration, secrets management,
deployment profiles, and configuration validation.
"""

import os
import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DeploymentEnvironment(str, Enum):
    """Deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LoggingLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class DatabaseConfig:
    """Database configuration."""

    host: str
    port: int
    username: str
    password: str
    database: str
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    ssl: bool = True

    def get_connection_url(self) -> str:
        """Get database connection URL."""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )


@dataclass
class CacheConfig:
    """Cache configuration."""

    backend: str = "redis"
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ttl_seconds: int = 3600
    max_connections: int = 50

    def get_connection_url(self) -> str:
        """Get cache connection URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class SecurityConfig:
    """Security configuration."""

    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    cors_origins: List[str] = field(default_factory=list)
    rate_limit_requests: int = 100
    rate_limit_period_seconds: int = 60
    enable_2fa: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""

    enabled: bool = True
    metrics_collection_interval_seconds: int = 60
    health_check_interval_seconds: int = 30
    alert_check_interval_seconds: int = 10
    log_level: LoggingLevel = LoggingLevel.INFO
    structured_logging: bool = True
    audit_logging: bool = True
    performance_tracking: bool = True
    max_log_history: int = 10000
    max_metrics_history: int = 5000


@dataclass
class MLConfig:
    """ML configuration."""

    enabled: bool = True
    feature_extraction_batch_size: int = 1000
    model_update_interval_hours: int = 24
    anomaly_detection_sensitivity: float = 2.0
    forecast_periods: int = 10
    forecast_confidence: float = 0.95


@dataclass
class APIConfig:
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    debug: bool = False
    max_request_size: int = 52428800  # 50MB
    request_timeout_seconds: int = 30
    enable_docs: bool = True


@dataclass
class DeploymentConfig:
    """Complete deployment configuration."""

    environment: DeploymentEnvironment
    app_name: str
    version: str
    debug: bool
    database: DatabaseConfig
    cache: CacheConfig
    security: SecurityConfig
    monitoring: MonitoringConfig
    ml: MLConfig
    api: APIConfig
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "environment": self.environment.value,
            "app_name": self.app_name,
            "version": self.version,
            "debug": self.debug,
            "database": asdict(self.database),
            "cache": asdict(self.cache),
            "security": asdict(self.security),
            "monitoring": {
                **asdict(self.monitoring),
                "log_level": self.monitoring.log_level.value,
            },
            "ml": asdict(self.ml),
            "api": asdict(self.api),
            "extra": self.extra,
        }

    def validate(self) -> List[str]:
        """Validate configuration.

        Returns:
            List of validation errors
        """
        errors = []

        if self.environment == DeploymentEnvironment.PRODUCTION:
            if self.debug:
                errors.append("Debug mode cannot be enabled in production")
            if self.api.reload:
                errors.append("Auto-reload cannot be enabled in production")
            if len(self.security.secret_key) < 32:
                errors.append("Secret key must be at least 32 characters in production")
            if not self.database.ssl:
                errors.append("SSL must be enabled for database in production")

        if self.database.pool_size < 1:
            errors.append("Database pool size must be at least 1")

        if self.security.access_token_expire_minutes < 1:
            errors.append("Token expiry must be at least 1 minute")

        if self.api.workers < 1:
            errors.append("API workers must be at least 1")

        return errors


class ConfigurationManager:
    """Manages deployment configuration."""

    def __init__(self):
        """Initialize configuration manager."""
        self.config: Optional[DeploymentConfig] = None
        self.secrets: Dict[str, str] = {}

    def load_from_env(self) -> DeploymentConfig:
        """Load configuration from environment variables.

        Returns:
            Deployment configuration
        """
        env = os.getenv("ENVIRONMENT", "development").lower()
        environment = DeploymentEnvironment(env)

        # Database config
        database = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password"),
            database=os.getenv("DB_NAME", "competitive_intelligence"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            echo=environment == DeploymentEnvironment.DEVELOPMENT,
        )

        # Cache config
        cache = CacheConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=os.getenv("REDIS_PASSWORD"),
        )

        # Security config
        security = SecurityConfig(
            secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
            cors_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
        )

        # Monitoring config
        monitoring = MonitoringConfig(
            log_level=LoggingLevel(os.getenv("LOG_LEVEL", "INFO")),
            debug=environment == DeploymentEnvironment.DEVELOPMENT,
        )

        # ML config
        ml = MLConfig()

        # API config
        api = APIConfig(
            port=int(os.getenv("API_PORT", "8000")),
            workers=int(os.getenv("API_WORKERS", "4")),
            reload=environment == DeploymentEnvironment.DEVELOPMENT,
            debug=environment == DeploymentEnvironment.DEVELOPMENT,
        )

        self.config = DeploymentConfig(
            environment=environment,
            app_name="Competitive Intelligence Engine",
            version=os.getenv("VERSION", "1.0.0"),
            debug=environment == DeploymentEnvironment.DEVELOPMENT,
            database=database,
            cache=cache,
            security=security,
            monitoring=monitoring,
            ml=ml,
            api=api,
        )

        # Validate
        errors = self.config.validate()
        if errors:
            logger.warning(f"Configuration validation errors: {errors}")

        logger.info(f"Loaded configuration for {environment.value} environment")
        return self.config

    def load_from_file(self, path: str) -> DeploymentConfig:
        """Load configuration from JSON file.

        Args:
            path: Path to configuration file

        Returns:
            Deployment configuration
        """
        with open(path, "r") as f:
            config_dict = json.load(f)

        self.config = self._dict_to_config(config_dict)
        return self.config

    def get_config(self) -> DeploymentConfig:
        """Get current configuration.

        Returns:
            Deployment configuration

        Raises:
            RuntimeError: If no configuration loaded
        """
        if self.config is None:
            raise RuntimeError("No configuration loaded")
        return self.config

    def set_secret(self, key: str, value: str) -> None:
        """Set secret value.

        Args:
            key: Secret key
            value: Secret value
        """
        self.secrets[key] = value
        logger.debug(f"Set secret: {key}")

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get secret value.

        Args:
            key: Secret key
            default: Default value if not found

        Returns:
            Secret value or default
        """
        return self.secrets.get(key, default)

    @staticmethod
    def _dict_to_config(data: Dict[str, Any]) -> DeploymentConfig:
        """Convert dictionary to config object.

        Args:
            data: Configuration dictionary

        Returns:
            Deployment configuration
        """
        environment = DeploymentEnvironment(data.get("environment", "development"))

        database = DatabaseConfig(**data.get("database", {}))
        cache = CacheConfig(**data.get("cache", {}))
        security = SecurityConfig(**data.get("security", {}))
        monitoring_data = data.get("monitoring", {})
        monitoring_data["log_level"] = LoggingLevel(monitoring_data.get("log_level", "INFO"))
        monitoring = MonitoringConfig(**monitoring_data)
        ml = MLConfig(**data.get("ml", {}))
        api = APIConfig(**data.get("api", {}))

        return DeploymentConfig(
            environment=environment,
            app_name=data.get("app_name", "Competitive Intelligence Engine"),
            version=data.get("version", "1.0.0"),
            debug=data.get("debug", False),
            database=database,
            cache=cache,
            security=security,
            monitoring=monitoring,
            ml=ml,
            api=api,
            extra=data.get("extra", {}),
        )


# Singleton instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get configuration manager singleton."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
        logger.info("Initialized ConfigurationManager")
    return _config_manager


def get_deployment_config() -> DeploymentConfig:
    """Get deployment configuration.

    Returns:
        Deployment configuration
    """
    manager = get_config_manager()
    if manager.config is None:
        manager.load_from_env()
    return manager.get_config()
