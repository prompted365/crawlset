"""
Configuration management using pydantic-settings.

Provides type-safe configuration loading from environment variables.
"""
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All settings can be overridden via environment variables.
    For example, DATABASE_URL can be set as an environment variable.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host address")
    port: int = Field(default=8080, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    reload: bool = Field(default=False, description="Enable auto-reload on code changes")

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/websets.db",
        description="SQLAlchemy async database URL",
    )
    database_echo: bool = Field(
        default=False,
        description="Enable SQLAlchemy SQL logging",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure SQLite URLs use the async driver."""
        if v.startswith("sqlite://"):
            # Convert to async SQLite driver
            return v.replace("sqlite://", "sqlite+aiosqlite://")
        return v

    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: List[str] = Field(default=["*"], description="Allowed CORS methods")
    cors_allow_headers: List[str] = Field(default=["*"], description="Allowed CORS headers")

    # RuVector Configuration
    ruvector_url: str = Field(
        default="http://localhost:6333",
        description="RuVector Rust service URL",
    )
    ruvector_data_dir: Path = Field(
        default=Path("./data/ruvector"),
        description="RuVector data directory (used by Rust service)",
    )
    ruvector_enable_gnn: bool = Field(
        default=True,
        description="Enable Graph Neural Network features",
    )
    ruvector_enable_graph: bool = Field(
        default=True,
        description="Enable knowledge graph features",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence-transformers embedding model",
    )
    embedding_batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation",
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for Celery",
    )

    # Requesty AI Configuration
    requesty_base_url: str = Field(
        default="https://router.requesty.ai/v1",
        description="Requesty AI router base URL",
    )
    requesty_api_key: Optional[str] = Field(
        default=None,
        description="Requesty AI API key",
    )
    requesty_default_model: str = Field(
        default="google/gemini-2.5-flash",
        description="Default LLM model or alias",
    )

    # Crawler Configuration
    playwright_headless: bool = Field(
        default=True,
        description="Run Playwright in headless mode",
    )
    crawler_timeout: int = Field(
        default=30000,
        description="Crawler timeout in milliseconds",
    )
    crawler_user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent for web crawling",
    )

    # Monitoring Configuration
    scheduler_timezone: str = Field(
        default="UTC",
        description="Default timezone for scheduler",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @property
    def sqlite_path(self) -> Path:
        """Get the SQLite database file path."""
        if "sqlite" in self.database_url:
            # Extract path from URL
            path_str = self.database_url.split("///")[-1]
            return Path(path_str)
        raise ValueError("Not a SQLite database URL")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    This function implements a singleton pattern to ensure
    settings are only loaded once.

    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.

    Useful for testing or when environment variables change.

    Returns:
        New Settings instance
    """
    global _settings
    _settings = Settings()
    return _settings
