"""Configuration for the application."""

from pydantic import BaseSettings


class Settings(BaseSettings):
    github_token: str | None = None
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
