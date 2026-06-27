"""Carga y guarda datos del usuario desde ~/.keel/."""

from pathlib import Path

from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona
from keel.models.config import ConfigKeel


_KEEL_DIR = Path.home() / ".keel"


def keel_dir() -> Path:
    _KEEL_DIR.mkdir(parents=True, exist_ok=True)
    return _KEEL_DIR


# ── cifrado transparente ──────────────────────────────────────────────────────

def _cifrado_activo() -> bool:
    return (_KEEL_DIR / ".cifrado").exists()


def _leer(ruta: Path) -> str:
    data = ruta.read_bytes()
    if _cifrado_activo():
        from keel.security.cifrado import descifrar, es_cifrado
        from keel.security.llave import obtener_clave
        if es_cifrado(data):
            data = descifrar(data, obtener_clave(_KEEL_DIR))
    return data.decode()


def _escribir(ruta: Path, contenido: str) -> None:
    data = contenido.encode()
    if _cifrado_activo():
        from keel.security.cifrado import cifrar
        from keel.security.llave import obtener_clave
        data = cifrar(data, obtener_clave(_KEEL_DIR))
    ruta.write_bytes(data)


# ── API pública (sin cambios de interfaz) ────────────────────────────────────

def cargar_perfil() -> PerfilUsuario:
    ruta = keel_dir() / "perfil.json"
    if not ruta.exists():
        raise FileNotFoundError(
            f"Perfil no encontrado en {ruta}.\n"
            "Crea uno con: keel init"
        )
    return PerfilUsuario.model_validate_json(_leer(ruta))


def guardar_perfil(perfil: PerfilUsuario) -> None:
    ruta = keel_dir() / "perfil.json"
    _escribir(ruta, perfil.model_dump_json(indent=2))


def cargar_aliases() -> dict:
    import json
    ruta = keel_dir() / "aliases.json"
    if not ruta.exists():
        return {}
    return json.loads(_leer(ruta))


def guardar_aliases(aliases: dict) -> None:
    import json
    ruta = keel_dir() / "aliases.json"
    _escribir(ruta, json.dumps(aliases, indent=2, ensure_ascii=False))


def resolver_alias(nombre: str) -> str:
    """Devuelve el nombre real si 'nombre' es un alias; si no, lo devuelve tal cual."""
    aliases = cargar_aliases()
    return aliases.get(nombre.lower(), nombre)


def cargar_persona(nombre: str) -> Persona:
    ruta = keel_dir() / "personas" / f"{nombre.lower()}.json"
    if not ruta.exists():
        nombre = resolver_alias(nombre)
        ruta = keel_dir() / "personas" / f"{nombre.lower()}.json"
    if not ruta.exists():
        return Persona(nombre=nombre)
    return Persona.model_validate_json(_leer(ruta))


def guardar_persona(persona: Persona) -> None:
    carpeta = keel_dir() / "personas"
    carpeta.mkdir(exist_ok=True)
    ruta = carpeta / f"{persona.nombre.lower()}.json"
    _escribir(ruta, persona.model_dump_json(indent=2))


def cargar_config() -> ConfigKeel:
    ruta = keel_dir() / "config.json"
    if not ruta.exists():
        return ConfigKeel()
    return ConfigKeel.model_validate_json(_leer(ruta))


def guardar_config(config: ConfigKeel) -> None:
    ruta = keel_dir() / "config.json"
    _escribir(ruta, config.model_dump_json(indent=2))


def cargar_notas() -> list:
    from keel.models.nota import Nota
    ruta = keel_dir() / "notas.json"
    if not ruta.exists():
        return []
    import json
    datos = json.loads(_leer(ruta))
    return [Nota.model_validate(d) for d in datos]


def guardar_notas(notas: list) -> None:
    import json
    ruta = keel_dir() / "notas.json"
    _escribir(ruta, json.dumps([n.model_dump() for n in notas], indent=2, ensure_ascii=False))


def agregar_nota(nota) -> None:
    notas = cargar_notas()
    notas.append(nota)
    guardar_notas(notas)


def eliminar_nota(nota_id: str) -> bool:
    notas = cargar_notas()
    nuevas = [n for n in notas if n.id != nota_id]
    if len(nuevas) == len(notas):
        return False
    guardar_notas(nuevas)
    return True
