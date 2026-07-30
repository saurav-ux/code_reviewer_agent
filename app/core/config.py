"""Configuration for the application."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    github_token: str | None = None
    github_webhook_secret: str | None = None
    github_api: str = "https://api.github.com"
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
