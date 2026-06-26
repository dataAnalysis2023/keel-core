"""Almacenamiento vectorial con LanceDB — búsqueda semántica en historial.

Tabla única `conversaciones` en ~/.keel/vectorial/.
Cada registro: persona, fecha, resumen, temas, vector.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keel.embedder.base import EmbedderBase

_TABLA = "conversaciones"


def _db_path() -> Path:
    from keel.storage.local import keel_dir
    return keel_dir() / "vectorial"


def _abrir_db():
    import lancedb
    return lancedb.connect(str(_db_path()))


def _abrir_tabla(db):
    """Abre la tabla si existe, devuelve None si no."""
    try:
        return db.open_table(_TABLA)
    except Exception:
        return None


def indexar_conversacion(
    persona: str,
    fecha: str,
    resumen: str,
    temas: list[str],
    embedder: "EmbedderBase",
) -> None:
    """Agrega un registro al índice vectorial."""
    vector = embedder.embed(f"{resumen} {' '.join(temas)}")
    registro = {
        "persona": persona,
        "fecha": fecha,
        "resumen": resumen,
        "temas": ", ".join(temas),
        "vector": vector,
    }
    db = _abrir_db()
    tabla = _abrir_tabla(db)
    if tabla is not None:
        tabla.add([registro])
    else:
        db.create_table(_TABLA, data=[registro])


def buscar_similar(
    persona: str,
    texto: str,
    embedder: "EmbedderBase",
    n: int = 3,
) -> list[dict]:
    """Retorna las n conversaciones más similares semánticamente."""
    db = _abrir_db()
    tabla = _abrir_tabla(db)
    if tabla is None:
        return []

    vector = embedder.embed(texto)
    try:
        filas = (
            tabla.search(vector)
            .where(f"persona = '{persona}'")
            .limit(n)
            .to_list()
        )
        return [
            {
                "persona": r["persona"],
                "fecha": r["fecha"],
                "resumen": r["resumen"],
                "temas": r["temas"],
            }
            for r in filas
        ]
    except Exception:
        return []


def total_indexados(persona: str | None = None) -> int:
    """Cuenta registros indexados, opcionalmente filtrado por persona."""
    db = _abrir_db()
    tabla = _abrir_tabla(db)
    if tabla is None:
        return 0
    if persona:
        try:
            filas = tabla.search().where(f"persona = '{persona}'").to_list()
            return len(filas)
        except Exception:
            return 0
    return tabla.count_rows()
