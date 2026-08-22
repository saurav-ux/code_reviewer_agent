"""FastAPI application entrypoint for the code-review-agent app."""

import logging
import sys
import os
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI

from app.api import webhook

# Prepare logs directory
LOGS_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Common formatter
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

# Stream handler for console (stdout)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)

# Rotating file handler
file_handler = RotatingFileHandler(
    os.path.join(LOGS_DIR, "app.log"), maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(formatter)

# Configure root logger to use both handlers
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers and attach ours
for h in list(root_logger.handlers):
    root_logger.removeHandler(h)

root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)

# Enable debug-level output for the webhook logger (change to INFO to quiet)
logging.getLogger("code_review_agent.webhook").setLevel(logging.DEBUG)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    The application exposes a health-check endpoint and registers the GitHub
    webhook router under the ``/github`` prefix.

    Returns:
        A configured FastAPI application instance.
    """
    app = FastAPI(title="code-review-agent")

    @app.get("/")
    def health() -> dict[str, str]:
        """Return the application health status.

        Returns:
            A dictionary indicating that the application is running.
        """
        return {"status": "running"}

    app.include_router(webhook.router, prefix="/github")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
