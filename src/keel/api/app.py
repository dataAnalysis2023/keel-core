"""Instancia FastAPI de keel-core."""

from fastapi import FastAPI

from keel.api.routers import sistema, perfil, personas, respond
from keel.api.routers.buscar import router as buscar_router
from keel.api.routers.reflexion import router as reflexion_router
from keel.api.routers.agenda_router import router as agenda_router
from keel.api.routers.aprendizaje_router import router as aprendizaje_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="keel-core API",
        description="Motor de extensión cognitiva personal — API REST local.",
        version="0.2.0",
        docs_url="/docs",
    )

    app.include_router(sistema.router)
    app.include_router(perfil.router)
    app.include_router(personas.router)
    app.include_router(respond.router)
    app.include_router(buscar_router)
    app.include_router(reflexion_router)
    app.include_router(agenda_router)
    app.include_router(aprendizaje_router)

    return app


app = create_app()
