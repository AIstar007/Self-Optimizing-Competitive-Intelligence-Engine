"""Application configuration management."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    url: str = Field(default="sqlite:///./test.db", alias="DATABASE_URL")
    pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")
    ssl: bool = Field(default=False, alias="DATABASE_SSL")

    class Config:
        case_sensitive = False


class RedisSettings(BaseSettings):
    """Redis/Cache configuration."""

    url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    ttl: int = Field(default=300, alias="CACHE_TTL")

    class Config:
        case_sensitive = False


class SecuritySettings(BaseSettings):
    """Security configuration."""

    jwt_secret: str = Field(default="dev-secret-key", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration: int = Field(default=86400, alias="JWT_EXPIRATION")
    https_only: bool = Field(default=False, alias="HTTPS_ONLY")
    secure_cookies: bool = Field(default=False, alias="SECURE_COOKIES")

    class Config:
        case_sensitive = False


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", alias="OPENAI_MODEL")
    openai_organization: Optional[str] = Field(default=None, alias="OPENAI_ORGANIZATION")
    
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-opus-20240229", alias="ANTHROPIC_MODEL")
    
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    class Config:
        case_sensitive = False


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="info", alias="LOG_LEVEL")
    format: str = Field(default="text", alias="LOG_FORMAT")
    file: str = Field(default="logs/app.log", alias="LOG_FILE")
    max_size: int = Field(default=10485760, alias="LOG_MAX_SIZE")
    backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")

    class Config:
        case_sensitive = False


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""

    enabled: bool = Field(default=False, alias="ENABLE_METRICS")
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    datadog_enabled: bool = Field(default=False, alias="DATADOG_ENABLED")
    datadog_api_key: Optional[str] = Field(default=None, alias="DATADOG_API_KEY")
    prometheus_enabled: bool = Field(default=False, alias="PROMETHEUS_ENABLED")

    class Config:
        case_sensitive = False


class RateLimitingSettings(BaseSettings):
    """Rate limiting configuration."""

    enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    requests: int = Field(default=1000, alias="RATE_LIMIT_REQUESTS")
    window: int = Field(default=3600, alias="RATE_LIMIT_WINDOW")

    class Config:
        case_sensitive = False


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    env: str = Field(default="development", alias="ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    # Server
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    workers: int = Field(default=1, alias="WORKERS")
    reload: bool = Field(default=False, alias="RELOAD")

    # Features
    enable_swagger: bool = Field(default=True, alias="ENABLE_SWAGGER")
    enable_metrics: bool = Field(default=False, alias="ENABLE_METRICS")
    enable_profiling: bool = Field(default=False, alias="ENABLE_PROFILING")

    # CORS
    cors_origins: list = Field(default=["*"], alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=False, alias="CORS_ALLOW_CREDENTIALS")

    # Sub-configurations
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    security: SecuritySettings = SecuritySettings()
    llm: LLMSettings = LLMSettings()
    logging: LoggingSettings = LoggingSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    rate_limiting: RateLimitingSettings = RateLimitingSettings()

    class Config:
        case_sensitive = False
        env_file = f".env.{os.getenv('ENV', 'development')}"

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"

    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.env == "testing"


# Global settings instance
settings = Settings()
