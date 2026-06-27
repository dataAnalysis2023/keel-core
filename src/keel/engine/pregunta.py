"""Motor de preguntas sobre el historial de una o todas las personas."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keel.models.persona import Persona


def construir_prompt_pregunta(
    pregunta: str,
    persona: "Persona | None",
    perfil_nombre: str,
    contexto_relevante: list[dict],
) -> str:
    """Construye el prompt para responder una pregunta.

    Si persona es None, el contexto abarca todas las personas (modo global).
    """
    if persona is not None:
        partes = [
            f"Eres el asistente personal de {perfil_nombre}.",
            f"El usuario tiene una pregunta sobre su relación con {persona.nombre}.",
            "",
        ]
        if persona.rol or persona.estado_actual:
            partes.append(f"Contexto de {persona.nombre}:")
            if persona.rol:
                partes.append(f"- Rol: {persona.rol}")
            if persona.estado_actual:
                partes.append(f"- Estado actual: {persona.estado_actual}")
            if persona.tono_relacional and persona.tono_relacional != "neutro":
                partes.append(f"- Tono relacional: {persona.tono_relacional}")
            partes.append("")
    else:
        partes = [
            f"Eres el asistente personal de {perfil_nombre}.",
            "El usuario tiene una pregunta sobre sus relaciones personales.",
            "",
        ]

    if contexto_relevante:
        partes.append(f"Fragmentos relevantes del historial ({len(contexto_relevante)}):")
        for r in contexto_relevante:
            quien = f"{r['persona']} · " if persona is None and r.get("persona") else ""
            temas = f" [{', '.join(r['temas'])}]" if r.get("temas") else ""
            partes.append(f"- [{r['fecha']}] {quien}{temas}: {r['resumen']}")
        partes.append("")
    else:
        partes.append(
            "No se encontraron fragmentos de historial relevantes para esta pregunta."
        )
        partes.append("")

    partes += [
        f"Pregunta: {pregunta}",
        "",
        "Responde en español, de forma concisa y directa (máximo 5-8 líneas). "
        "Basa tu respuesta únicamente en el historial disponible. "
        "Si no hay información suficiente para responder, dilo explícitamente.",
    ]

    return "\n".join(partes)


def respuesta_sin_llm(contexto_relevante: list[dict], persona_nombre: str | None = None) -> str:
    """Devuelve el historial relevante como texto cuando no hay LLM disponible."""
    if not contexto_relevante:
        if persona_nombre:
            return f"No hay historial registrado con {persona_nombre} que responda a esa pregunta."
        return "No hay historial registrado que responda a esa pregunta."

    titulo = f"Historial relevante con {persona_nombre}:" if persona_nombre else "Historial relevante:"
    lineas = [titulo, ""]
    for r in contexto_relevante:
        quien = f"[{r['persona']}] " if not persona_nombre and r.get("persona") else ""
        temas = f" [{', '.join(r['temas'])}]" if r.get("temas") else ""
        lineas.append(f"• [{r['fecha']}] {quien}{temas}: {r['resumen']}")
    return "\n".join(lineas)
