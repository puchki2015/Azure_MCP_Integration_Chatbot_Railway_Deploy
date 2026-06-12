from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    APP_NAME: str = "Azure AI Ops"

    ENVIRONMENT: str = "dev"

    API_PREFIX: str = "/api/v1"

    # Comma-separated browser origins allowed to call the API.
    # Example: "https://frontend-prod.up.railway.app,https://app.example.com"
    CORS_ORIGINS: str = ""

    OPENAI_API_KEY: str

    # Backwards-compatible default; legacy single-model code paths may still read this.
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_PLANNER_MODEL: str = "gpt-5.4-mini"
    OPENAI_SUMMARY_MODEL: str = "gpt-5.4-nano"
    OPENAI_EXECUTION_MODEL: str = "gpt-5.5"

    DATABASE_URL: str

    REDIS_URL: str

    # Entra Login
    ENTRA_TENANT_ID: str
    ENTRA_CLIENT_ID: str
    ALLOWED_USER_EMAILS: str = ""
    ADMIN_USER_EMAILS: str = ""

    # Local development helper
    DEV_BYPASS_AUTH: bool = False
    DEV_BYPASS_USER_EMAIL: str = "dev@example.com"
    DEV_BYPASS_USER_NAME: str = "Local Dev"

    # Azure MCP Authentication
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_CLIENT_SECRET: str
    AZURE_SUBSCRIPTION_ID: str

    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    AZURE_SPEECH_LANGUAGE: str = "en-US"

    def get_cors_origins(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

        if origins:
            return origins

        if self.ENVIRONMENT.lower() in {"dev", "development", "local"}:
            return [
                "http://localhost:3000",
                "http://localhost:5173"
            ]

        return []


@lru_cache
def get_settings():
    return Settings()
