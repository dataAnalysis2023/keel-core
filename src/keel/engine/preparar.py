"""Briefing pre-conversación: contexto relacional de una persona antes de hablar con ella."""

from datetime import date

from keel.models.persona import Persona


def briefing_a_markdown(persona: Persona, sintesis: str = "", n_recientes: int = 5) -> str:
    """Genera el briefing en Markdown sin LLM (estructura + datos)."""
    hoy = date.today().isoformat()
    lineas = [f"# Briefing — {persona.nombre} ({hoy})\n"]

    if persona.rol or persona.como_nos_conocemos:
        if persona.rol:
            lineas.append(f"**Rol:** {persona.rol}")
        if persona.como_nos_conocemos:
            lineas.append(f"**Contexto:** {persona.como_nos_conocemos}")
        if persona.tono_relacional and persona.tono_relacional != "neutro":
            lineas.append(f"**Tono relacional:** {persona.tono_relacional}")
        if persona.estado_actual:
            lineas.append(f"**Estado actual:** {persona.estado_actual}")
        if persona.sensibilidades:
            lineas.append(f"**Sensibilidades:** {', '.join(persona.sensibilidades)}")
        lineas.append("")

    if sintesis:
        lineas.append("## Síntesis\n")
        lineas.append(sintesis)
        lineas.append("")

    if persona.promesas_pendientes:
        lineas.append("## Compromisos pendientes\n")
        for pr in persona.promesas_pendientes:
            fecha = f" (hasta {pr.fecha_compromiso})" if pr.fecha_compromiso else ""
            lineas.append(f"- {pr.descripcion}{fecha}")
        lineas.append("")

    recientes = sorted(persona.historial_conversaciones, key=lambda c: c.fecha)[-n_recientes:]
    if recientes:
        lineas.append(f"## Últimas {len(recientes)} conversaciones\n")
        for c in recientes:
            temas = f" [{', '.join(c.temas)}]" if c.temas else ""
            lineas.append(f"- `{c.fecha}`{temas}: {c.resumen}")
        lineas.append("")

    temas = _temas_frecuentes(persona)
    if temas:
        lineas.append("## Temas frecuentes\n")
        lineas.append(", ".join(f"`{t}`" for t in temas))
        lineas.append("")

    return "\n".join(lineas)


def construir_prompt_briefing(persona: Persona, perfil_nombre: str, n_recientes: int = 5) -> str:
    """Construye el prompt para que el LLM genere la síntesis."""
    partes = [
        f"Eres el asistente personal de {perfil_nombre}.",
        f"Va a hablar con {persona.nombre}.",
        "En 3-5 líneas, dile lo más importante que debe recordar para esta conversación.",
        "Sé directo. Sin listas. Sin encabezados. Solo el resumen ejecutivo.\n",
    ]

    if persona.rol:
        partes.append(f"Rol de {persona.nombre}: {persona.rol}")
    if persona.como_nos_conocemos:
        partes.append(f"Contexto: {persona.como_nos_conocemos}")
    if persona.estado_actual:
        partes.append(f"Estado actual: {persona.estado_actual}")
    if persona.sensibilidades:
        partes.append(f"Sensibilidades: {', '.join(persona.sensibilidades)}")

    if persona.promesas_pendientes:
        items = "; ".join(
            f"{pr.descripcion}" + (f" (vence {pr.fecha_compromiso})" if pr.fecha_compromiso else "")
            for pr in persona.promesas_pendientes
        )
        partes.append(f"Compromisos pendientes: {items}")

    recientes = sorted(persona.historial_conversaciones, key=lambda c: c.fecha)[-n_recientes:]
    if recientes:
        items = "; ".join(
            f"{c.fecha}: {c.resumen}" + (f" [{', '.join(c.temas)}]" if c.temas else "")
            for c in recientes
        )
        partes.append(f"Conversaciones recientes: {items}")

    temas = _temas_frecuentes(persona)
    if temas:
        partes.append(f"Temas recurrentes: {', '.join(temas)}")

    return "\n".join(partes)


def _temas_frecuentes(persona: Persona, top: int = 5) -> list[str]:
    from collections import Counter
    contador: Counter = Counter()
    for conv in persona.historial_conversaciones:
        for tema in conv.temas:
            if tema.strip():
                contador[tema.strip().lower()] += 1
    return [t for t, _ in contador.most_common(top) if contador[t] > 1]
