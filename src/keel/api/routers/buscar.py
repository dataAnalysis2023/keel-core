from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/buscar", tags=["buscar"])


class BuscarRequest(BaseModel):
    texto: str
    persona: str | None = None
    top: int = 5


@router.post("")
def buscar(req: BuscarRequest):
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.busqueda import buscar_global

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas_lista = [Persona.model_validate_json(a.read_text()) for a in archivos]

    resultados = buscar_global(
        req.texto,
        personas_lista,
        embedder=None,
        top=req.top,
        filtro_persona=req.persona,
    )
    return {"resultados": resultados, "total": len(resultados)}
