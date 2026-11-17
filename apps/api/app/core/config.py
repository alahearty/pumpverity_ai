from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PETROSENSE_",
        extra="ignore",
    )

    project_name: str = "PUMPVERITY AI"
    version: str = "0.6.0"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_days: int = Field(default=7, ge=1, le=30)
    refresh_cookie_name: str = "petrosense_refresh"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    database_url: str = "sqlite:///./data/petrosense.db"
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"
    demo_seed_enabled: bool = True
    demo_password: SecretStr | None = None
    edge_sync_max_retries: int = Field(default=10, ge=1, le=100)
    copilot_enabled: bool = True
    copilot_provider: Literal["deterministic", "openai_compatible"] = "deterministic"
    copilot_model: str = "gpt-4.1-mini"
    copilot_base_url: str = ""
    copilot_api_key: SecretStr | None = None
    copilot_timeout_seconds: float = Field(default=20.0, ge=1, le=120)
    copilot_max_tool_calls: int = Field(default=5, ge=1, le=10)
    copilot_history_limit: int = Field(default=12, ge=0, le=40)
    mcp_transport: Literal["memory", "http"] = "memory"
    mcp_server_url: str = "http://127.0.0.1:8010/mcp"
    mcp_service_token: SecretStr | None = None
    mcp_tool_timeout_seconds: float = Field(default=15.0, ge=1, le=120)
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8010, ge=1, le=65535)
    reports_directory: str = "data/reports"

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        if not value.strip():
            return ""
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def refresh_cookie_path(self) -> str:
        return f"{self.api_v1_prefix}/auth"

    @property
    def mcp_service_token_value(self) -> str:
        if self.mcp_service_token is not None:
            return self.mcp_service_token.get_secret_value()
        return self.secret_key

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_sqlite_directory(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    raw_path = database_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:":
        return
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    candidate.parent.mkdir(parents=True, exist_ok=True)

