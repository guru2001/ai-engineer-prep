from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Google Gemini — the SDK reads GEMINI_API_KEY (or GOOGLE_API_KEY) from the
    # environment automatically. Get a FREE key at https://aistudio.google.com/apikey
    # gemini-2.0-flash is fast, free-tier eligible, and reads PDFs directly.
    gemini_model: str = "gemini-2.0-flash"

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
