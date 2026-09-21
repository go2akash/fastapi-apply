"""
Application settings loaded from environment variables.

WHY pydantic-settings?
-----------------------
In production, configuration comes from environment variables (set by
Docker, Kubernetes, or a .env file). pydantic-settings:
1. Reads env vars automatically
2. Validates types (crashes on startup if DATABASE_URL is missing, not at runtime)
3. Provides type hints for IDE autocomplete

This is the same concept as:
- Go: envconfig or viper
- Node: dotenv + joi validation
- Java: Spring @ConfigurationProperties
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    environment: str = "development"  # "development" or "production"
    groq_api: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
