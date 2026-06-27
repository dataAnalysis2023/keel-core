"""Motor de búsqueda en historial de conversaciones."""

from __future__ import annotations

from typing import TYPE_CHECKING

from keel.storage.vectorial import buscar_similar

if TYPE_CHECKING:
    from keel.embedder.base import EmbedderBase
    from keel.models.persona import Persona


def buscar_global(
    texto: str,
    personas: list["Persona"],
    embedder: "EmbedderBase | None" = None,
    top: int = 5,
    filtro_persona: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
) -> list[dict]:
    """Busca en el historial de todas las personas.

    Con embedder: búsqueda semántica en LanceDB.
    Sin embedder: búsqueda por subcadena en resúmenes y temas.

    Devuelve lista de dicts con keys: persona, fecha, resumen, temas, modo.
    """
    if filtro_persona:
        personas = [p for p in personas if p.nombre.lower() == filtro_persona.lower()]

    if embedder:
        resultados = _buscar_semantico(texto, personas, embedder, top * 3)
    else:
        resultados = _buscar_keywords(texto, personas, top * 3)

    if desde:
        resultados = [r for r in resultados if r.get("fecha", "") >= desde]
    if hasta:
        resultados = [r for r in resultados if r.get("fecha", "") <= hasta]

    return resultados[:top]


def _buscar_semantico(
    texto: str,
    personas: list["Persona"],
    embedder: "EmbedderBase",
    top: int,
) -> list[dict]:
    resultados = []
    nombres = [p.nombre for p in personas]

    for nombre in nombres:
        parciales = buscar_similar(nombre, texto, embedder, n=top)
        for r in parciales:
            resultados.append({**r, "modo": "semántico"})

    # LanceDB no devuelve score en to_list sin .metric — ordenamos por fecha descendente
    resultados.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return resultados[:top]


def _buscar_keywords(
    texto: str,
    personas: list["Persona"],
    top: int,
) -> list[dict]:
    termino = texto.lower()
    resultados = []

    for persona in personas:
        for conv in persona.historial_conversaciones:
            haystack = f"{conv.resumen} {' '.join(conv.temas)}".lower()
            if termino in haystack:
                resultados.append({
                    "persona": persona.nombre,
                    "fecha": conv.fecha,
                    "resumen": conv.resumen,
                    "temas": ", ".join(conv.temas),
                    "modo": "keyword",
                })

    resultados.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return resultados[:top]


def buscar_notas(
    texto: str,
    notas: list,
    embedder: "EmbedderBase | None" = None,
    top: int = 5,
) -> list[dict]:
    """Busca en notas personales. Devuelve dicts compatibles con buscar_global."""
    if embedder:
        from keel.storage.vectorial import buscar_similar
        resultados = buscar_similar("_notas", texto, embedder, n=top)
        return [{**r, "persona": "[nota]", "modo": "semántico"} for r in resultados]

    termino = texto.lower()
    resultados = []
    for nota in notas:
        haystack = f"{nota.contenido} {' '.join(nota.temas)}".lower()
        if termino in haystack:
            resultados.append({
                "persona": "[nota]",
                "fecha": nota.fecha,
                "resumen": nota.contenido,
                "temas": nota.temas,
                "modo": "keyword",
            })
    resultados.sort(key=lambda x: x["fecha"], reverse=True)
    return resultados[:top]
