from __future__ import annotations

import asyncio

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.webhooks import router as webhook_router
from app.config import settings
from app.db import init_db
from app.queue import process_audit_queue


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="1.0.0")

    @app.on_event("startup")
    async def startup_event() -> None:
        await init_db()
        app.state.audit_worker = asyncio.create_task(process_audit_queue())

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        if hasattr(app.state, "audit_worker"):
            app.state.audit_worker.cancel()

    app.include_router(health_router)
    app.include_router(webhook_router)
    return app


app = create_app()
