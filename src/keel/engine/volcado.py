"""Genera un dump completo de contexto optimizado para LLMs."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keel.models.perfil import PerfilUsuario
    from keel.models.persona import Persona
    from keel.models.nota import Nota


def volcar_a_markdown(
    perfil: "PerfilUsuario",
    personas: list["Persona"],
    recientes: int = 3,
    con_framing: bool = True,
    notas: "list[Nota] | None" = None,
    notas_top: int = 5,
) -> str:
    """Genera el Markdown completo para pegar en un LLM externo."""
    hoy = date.today().isoformat()
    lineas: list[str] = []

    if con_framing:
        lineas += [
            f"Eres el asistente personal de {perfil.nombre}. "
            "Usa el siguiente contexto sobre sus relaciones y compromisos para responder "
            "preguntas, recordar acuerdos o ayudar a redactar mensajes.",
            "",
            "---",
            "",
        ]

    lineas += [f"# Contexto Keel — {perfil.nombre} · {hoy}", ""]

    # ── Perfil ────────────────────────────────────────────────────────────────
    lineas.append("## Perfil\n")
    if perfil.valores:
        lineas.append(f"- **Valores**: {', '.join(perfil.valores)}")
    if perfil.voz.tono:
        lineas.append(f"- **Tono**: {perfil.voz.tono}")
    if perfil.voz.registro:
        lineas.append(f"- **Registro**: {perfil.voz.registro}")
    if perfil.voz.frases_caracteristicas:
        lineas.append(
            f"- **Frases características**: {'; '.join(perfil.voz.frases_caracteristicas[:3])}"
        )
    if perfil.contexto_vital:
        for k, v in perfil.contexto_vital.items():
            lineas.append(f"- **{k}**: {v}")
    lineas.append("")

    # ── Personas ──────────────────────────────────────────────────────────────
    total_convs = sum(len(p.historial_conversaciones) for p in personas)
    lineas.append(f"## Personas ({len(personas)} · {total_convs} conversaciones)\n")

    for p in personas:
        lineas.append(f"### {p.nombre}")
        if p.rol:
            lineas.append(f"- **Rol**: {p.rol}")
        if p.como_nos_conocemos:
            lineas.append(f"- **Contexto**: {p.como_nos_conocemos}")
        if p.tono_relacional and p.tono_relacional != "neutro":
            lineas.append(f"- **Tono relacional**: {p.tono_relacional}")
        if p.sensibilidades:
            lineas.append(f"- **Sensibilidades**: {', '.join(p.sensibilidades)}")
        if p.estado_actual:
            lineas.append(f"- **Estado actual**: {p.estado_actual}")
        if p.ultima_interaccion:
            lineas.append(f"- **Último contacto**: {p.ultima_interaccion}")

        if p.promesas_pendientes:
            for pr in p.promesas_pendientes:
                icono = _icono_promesa(pr.fecha_compromiso, hoy)
                fecha = f" · hasta {pr.fecha_compromiso}" if pr.fecha_compromiso else ""
                lineas.append(f"- **Promesa** {icono}: {pr.descripcion}{fecha}")

        recents = sorted(p.historial_conversaciones, key=lambda c: c.fecha)[-recientes:]
        if recents:
            lineas.append(f"- **Historial reciente** ({len(recents)}):")
            for c in recents:
                temas = f" [{', '.join(c.temas)}]" if c.temas else ""
                lineas.append(f"  - `{c.fecha}`{temas}: {c.resumen}")

        lineas.append("")

    # ── Agenda global ─────────────────────────────────────────────────────────
    pendientes = [
        (p.nombre, pr)
        for p in personas
        for pr in p.promesas_pendientes
    ]
    if pendientes:
        lineas.append("## Agenda (promesas pendientes)\n")
        pendientes_ord = sorted(
            pendientes,
            key=lambda x: x[1].fecha_compromiso or "9999-99-99",
        )
        for nombre, pr in pendientes_ord:
            icono = _icono_promesa(pr.fecha_compromiso, hoy)
            fecha = f" — {pr.fecha_compromiso}" if pr.fecha_compromiso else ""
            lineas.append(f"- {icono} **{nombre}**: {pr.descripcion}{fecha}")
        lineas.append("")

    # ── Notas recientes ───────────────────────────────────────────────────────
    if notas:
        recientes_notas = sorted(notas, key=lambda n: n.fecha, reverse=True)[:notas_top]
        lineas.append(f"## Notas recientes ({len(recientes_notas)})\n")
        for nota in recientes_notas:
            temas_str = f" [{', '.join(nota.temas)}]" if nota.temas else ""
            lineas.append(f"- `{nota.fecha}`{temas_str}: {nota.contenido}")
        lineas.append("")

    return "\n".join(lineas)


def _icono_promesa(fecha_compromiso: str | None, hoy: str) -> str:
    if not fecha_compromiso:
        return "🟢"
    if fecha_compromiso < hoy:
        return "🔴"
    from datetime import date, timedelta
    limite_amarillo = (date.fromisoformat(hoy) + timedelta(days=3)).isoformat()
    if fecha_compromiso <= limite_amarillo:
        return "🟡"
    return "🟢"
