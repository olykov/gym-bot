from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Gym Bot Admin"
    API_V1_STR: str = "/api/v1"

    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    # Auth secrets — required; no defaults to prevent insecure deployments.
    JWT_SECRET: str
    ADMIN_USER: str
    ADMIN_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("JWT_SECRET", "ADMIN_USER", "ADMIN_PASSWORD", mode="before")
    @classmethod
    def must_not_be_empty(cls, v: str, info: object) -> str:
        """Fail fast if a required secret env var is empty or unset."""
        if not v or not v.strip():
            field_name = getattr(info, "field_name", str(info))
            raise ValueError(f"{field_name} must be set and non-empty")
        return v

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
