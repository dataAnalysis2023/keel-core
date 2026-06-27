from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("")
def listar_agenda():
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from datetime import date

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    hoy = date.today().isoformat()

    pendientes = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        for idx, promesa in enumerate(p.promesas_pendientes):
            pendientes.append({
                "persona": p.nombre,
                "indice": idx,
                "descripcion": promesa.descripcion,
                "fecha_compromiso": promesa.fecha_compromiso,
                "vencida": bool(promesa.fecha_compromiso and promesa.fecha_compromiso < hoy),
            })

    return {"pendientes": pendientes, "total": len(pendientes)}


class CompletarRequest(BaseModel):
    indice: int


@router.post("/{persona}/completar")
def completar_promesa(persona: str, req: CompletarRequest):
    from keel.storage.local import cargar_persona, guardar_persona

    p = cargar_persona(persona)
    if req.indice < 0 or req.indice >= len(p.promesas_pendientes):
        raise HTTPException(status_code=404, detail=f"Índice {req.indice} fuera de rango")

    eliminada = p.promesas_pendientes.pop(req.indice)
    guardar_persona(p)
    return {"eliminada": eliminada.descripcion, "pendientes": len(p.promesas_pendientes)}


class PosponerRequest(BaseModel):
    indice: int
    fecha: str


@router.patch("/{persona}/posponer")
def posponer_promesa(persona: str, req: PosponerRequest):
    from keel.storage.local import cargar_persona, guardar_persona
    from datetime import date

    try:
        date.fromisoformat(req.fecha)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Fecha inválida: {req.fecha}")

    p = cargar_persona(persona)
    if req.indice < 0 or req.indice >= len(p.promesas_pendientes):
        raise HTTPException(status_code=404, detail=f"Índice {req.indice} fuera de rango")

    anterior = p.promesas_pendientes[req.indice].fecha_compromiso
    p.promesas_pendientes[req.indice].fecha_compromiso = req.fecha
    guardar_persona(p)
    return {"descripcion": p.promesas_pendientes[req.indice].descripcion, "anterior": anterior, "nueva": req.fecha}
