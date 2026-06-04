from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gym Bot Admin"
    API_V1_STR: str = "/api/v1"

    # Migration / ops DB credentials (superuser myuser, BYPASSRLS).
    # Used ONLY by Alembic and ops tooling; never by the running API.
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    # Runtime DB credentials — the API connects as this role at request time.
    # app_rw is NOSUPERUSER NOBYPASSRLS so RLS policies apply.
    # APP_DB_USER defaults to "app_rw" (the fixed name from GYM-32).
    APP_DB_USER: str = "app_rw"
    # APP_DB_PASSWORD is required; fail fast if unset (same pattern as JWT_SECRET).
    APP_DB_PASSWORD: str

    # Auth secrets — required; no defaults to prevent insecure deployments.
    JWT_SECRET: str
    ADMIN_USER: str
    ADMIN_PASSWORD: str

    # Service-to-service auth — required; the bot presents this token to
    # impersonate Telegram users without sharing JWT_SECRET.
    BOT_SERVICE_TOKEN: str

    # Redis URL for analytics cache (db index /1 keeps cache separate from bot FSM on /0).
    # Default points to the shared gymbot_redis service defined in docker-compose.
    # Override via REDIS_URL env var; not a secret (no credentials in the default).
    REDIS_URL: str = "redis://gymbot_redis:6379/1"

    # CORS — comma-separated list of allowed origins.
    # Override via CORS_ALLOW_ORIGINS env var in production.
    CORS_ALLOW_ORIGINS: str = "https://gymbot.olykov.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS_ALLOW_ORIGINS into a list of origin strings."""
        return [o.strip() for o in self.CORS_ALLOW_ORIGINS.split(",") if o.strip()]

    @field_validator(
        "JWT_SECRET",
        "ADMIN_USER",
        "ADMIN_PASSWORD",
        "BOT_SERVICE_TOKEN",
        "APP_DB_PASSWORD",
        mode="before",
    )
    @classmethod
    def must_not_be_empty(cls, v: str, info: object) -> str:
        """Fail fast if a required secret env var is empty or unset."""
        if not v or not v.strip():
            field_name = getattr(info, "field_name", str(info))
            raise ValueError(f"{field_name} must be set and non-empty")
        return v

    @property
    def DATABASE_URL(self) -> str:
        """Migration / ops URL connecting as the superuser (myuser, BYPASSRLS).

        Do NOT use this URL in request handlers — it bypasses RLS.
        Use ``APP_DATABASE_URL`` for runtime queries.
        """
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def APP_DATABASE_URL(self) -> str:
        """Runtime URL connecting as app_rw (NOSUPERUSER, NOBYPASSRLS).

        This is the URL used by the API engine for all request-time queries.
        RLS policies apply to this connection.
        """
        return (
            f"postgresql://{self.APP_DB_USER}:{self.APP_DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
