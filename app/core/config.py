"""Configuration for the applications."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    github_token: str | None = None
    github_webhook_secret: str | None = None
    github_api: str = "https://api.github.com"
    environment: str = "development"
    
    # Groq API configuration
    groq_api_key: str | None = None
    groq_model: str = "mixtral-8x7b-32768"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
