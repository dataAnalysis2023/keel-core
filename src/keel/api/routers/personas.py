from fastapi import APIRouter, HTTPException
from pathlib import Path

from keel.api.schemas import PersonaUpdate, PersonaResumen
from keel.models.persona import Persona
from keel.storage.local import cargar_persona, guardar_persona, keel_dir

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaResumen])
def list_personas():
    personas_dir = keel_dir() / "personas"
    if not personas_dir.exists():
        return []
    resultado = []
    for archivo in sorted(personas_dir.glob("*.json")):
        p = Persona.model_validate_json(archivo.read_text())
        resultado.append(PersonaResumen(
            nombre=p.nombre,
            rol=p.rol,
            tono_relacional=p.tono_relacional,
            total_conversaciones=len(p.historial_conversaciones),
            total_promesas=len(p.promesas_pendientes),
            ultima_interaccion=p.ultima_interaccion,
        ))
    return resultado


@router.get("/{nombre}", response_model=Persona)
def get_persona(nombre: str):
    p = cargar_persona(nombre)
    return p


@router.post("/{nombre}", response_model=Persona)
def update_persona(nombre: str, datos: PersonaUpdate):
    p = cargar_persona(nombre)
    if datos.rol is not None:
        p.rol = datos.rol
    if datos.como_nos_conocemos is not None:
        p.como_nos_conocemos = datos.como_nos_conocemos
    if datos.tono_relacional is not None:
        p.tono_relacional = datos.tono_relacional
    if datos.sensibilidades is not None:
        p.sensibilidades = datos.sensibilidades
    guardar_persona(p)
    return p
