"""Carga y guarda datos del usuario desde ~/.keel/."""

from pathlib import Path

from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona


_KEEL_DIR = Path.home() / ".keel"


def keel_dir() -> Path:
    _KEEL_DIR.mkdir(parents=True, exist_ok=True)
    return _KEEL_DIR


def cargar_perfil() -> PerfilUsuario:
    ruta = keel_dir() / "perfil.json"
    if not ruta.exists():
        raise FileNotFoundError(
            f"Perfil no encontrado en {ruta}.\n"
            "Crea uno con: keel init"
        )
    return PerfilUsuario.model_validate_json(ruta.read_text())


def guardar_perfil(perfil: PerfilUsuario) -> None:
    ruta = keel_dir() / "perfil.json"
    ruta.write_text(perfil.model_dump_json(indent=2))


def cargar_persona(nombre: str) -> Persona:
    ruta = keel_dir() / "personas" / f"{nombre.lower()}.json"
    if not ruta.exists():
        return Persona(nombre=nombre)
    return Persona.model_validate_json(ruta.read_text())


def guardar_persona(persona: Persona) -> None:
    carpeta = keel_dir() / "personas"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / f"{persona.nombre.lower()}.json"
    ruta.write_text(persona.model_dump_json(indent=2))
