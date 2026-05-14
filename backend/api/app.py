from fastapi import FastAPI

from ..config import settings
from .routers import chat, rag, workflow


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(chat.router)
    app.include_router(rag.router)
    app.include_router(workflow.router)
    return app


app = create_app()
