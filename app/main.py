"""FastAPI application entrypoint for the code-review-agent app."""

from fastapi import FastAPI
from app.api import webhook


def create_app() -> FastAPI:
    app = FastAPI(title="code-review-agent")

    @app.get("/")
    def health():
        return {"status": "running"}

    app.include_router(webhook.router, prefix="/github")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
