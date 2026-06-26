"""Instancia FastAPI de keel-core."""

from fastapi import FastAPI

from keel.api.routers import sistema, perfil, personas, respond


def create_app() -> FastAPI:
    app = FastAPI(
        title="keel-core API",
        description="Motor de extensión cognitiva personal — API REST local.",
        version="0.1.0",
        docs_url="/docs",
    )

    app.include_router(sistema.router)
    app.include_router(perfil.router)
    app.include_router(personas.router)
    app.include_router(respond.router)

    return app


app = create_app()
