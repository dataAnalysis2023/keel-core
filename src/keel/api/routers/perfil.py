from fastapi import APIRouter, HTTPException
from keel.models.perfil import PerfilUsuario
from keel.storage.local import cargar_perfil, guardar_perfil

router = APIRouter(prefix="/perfil", tags=["perfil"])


@router.get("", response_model=PerfilUsuario)
def get_perfil():
    try:
        return cargar_perfil()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("", response_model=PerfilUsuario)
def update_perfil(perfil: PerfilUsuario):
    guardar_perfil(perfil)
    return perfil
