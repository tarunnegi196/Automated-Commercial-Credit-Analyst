"""
Configuration management using Pydantic Settings.
All environment variables and application settings are validated here.
"""

from typing import Optional, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging


class DatabaseConfig(BaseSettings):
    """PostgreSQL database configuration."""
    
    host: str = Field(default="localhost", alias="POSTGRES_HOST")
    port: int = Field(default=5432, alias="POSTGRES_PORT")
    database: str = Field(default="credit_analyst", alias="POSTGRES_DB")
    user: str = Field(default="postgres", alias="POSTGRES_USER")
    password: str = Field(alias="POSTGRES_PASSWORD")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_connection_string(self) -> str:
        """Generate async SQLAlchemy connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class QdrantConfig(BaseSettings):
    """Qdrant vector database configuration."""
    
    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT")
    collection_name: str = Field(default="sec_filings", alias="QDRANT_COLLECTION_NAME")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def url(self) -> str:
        """Generate Qdrant connection URL."""
        return f"http://{self.host}:{self.port}"


class LLMConfig(BaseSettings):
    """LLM provider configuration."""
    
    api_key: str = Field(alias="GROQ_API_KEY")
    model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=4096)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class SECConfig(BaseSettings):
    """SEC EDGAR API configuration."""
    
    user_agent: str = Field(alias="SEC_USER_AGENT")
    base_url: str = Field(default="https://www.sec.gov")
    rate_limit_delay: float = Field(default=0.1)  # SEC requires 10 requests/second max
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str) -> str:
        """Ensure user agent follows SEC requirements."""
        if not v or "@" not in v:
            raise ValueError(
                "SEC_USER_AGENT must include name and email (e.g., 'YourName your@email.com')"
            )
        return v


class AppConfig(BaseSettings):
    """Application-wide configuration."""
    
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    timeout_seconds: int = Field(default=120, alias="TIMEOUT_SECONDS")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL"
    )
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper
    
    @property
    def log_level_int(self) -> int:
        """Get logging level as integer."""
        return getattr(logging, self.log_level)


class Settings(BaseSettings):
    """Master settings container."""
    
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sec: SECConfig = Field(default_factory=SECConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()