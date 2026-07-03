from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI — the SDK reads OPENAI_API_KEY from the environment automatically.
    # gpt-4.1-nano is the cheapest model that still supports structured outputs.
    # Override with OPENAI_MODEL (e.g. gpt-4o-mini, gpt-4.1-mini) for more quality.
    openai_model: str = "gpt-4.1-nano"

    # Storage. SQLite by default; set DATABASE_URL to a Postgres URL in prod.
    # PDF bytes live in the DB (see models.Document), so no file storage needed.
    database_url: str = "sqlite:///./doclens.db"

    # CORS — comma-separated list of allowed frontend origins.
    cors_origins: str = "http://localhost:5173"

    # Guardrails
    max_upload_mb: int = 25

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
