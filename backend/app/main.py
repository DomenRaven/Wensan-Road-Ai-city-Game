from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.services.bootstrap import run_startup_bootstrap
from app.routers import bootstrap, creative, edu_preview, generate, health, intent, play, sessions, wizard
from app.stores.session_store import StoreBackend, create_session_store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = get_settings()
    store, backend = create_session_store(settings)
    app.state.settings = settings
    app.state.session_store = store
    app.state.store_backend = backend
    app.state.bootstrap_report = run_startup_bootstrap(settings, store)
    yield


def create_app() -> FastAPI:
    settings: Settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(bootstrap.router)
    app.include_router(sessions.router)
    app.include_router(wizard.router)
    app.include_router(intent.router)
    app.include_router(creative.router)
    app.include_router(generate.router)
    app.include_router(play.router)
    app.include_router(edu_preview.router)
    return app


app = create_app()
