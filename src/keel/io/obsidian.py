"""Integración con Obsidian: escribe notas al vault con frontmatter YAML."""

from __future__ import annotations

from datetime import date
from pathlib import Path


_VAULT_DEFAULT = Path.home() / "Proyectos"
_CARPETA_KEEL = "keel"


def vault_path(vault: str | None = None) -> Path:
    return Path(vault) if vault else _VAULT_DEFAULT


def daily_note_path(vault: str | None = None) -> Path:
    hoy = date.today().isoformat()
    return vault_path(vault) / _CARPETA_KEEL / "diario" / f"{hoy}.md"


def reflexion_path(vault: str | None = None, fecha: str | None = None) -> Path:
    f = fecha or date.today().isoformat()
    return vault_path(vault) / _CARPETA_KEEL / "reflexiones" / f"reflexion-{f}.md"


def persona_note_path(nombre: str, vault: str | None = None) -> Path:
    return vault_path(vault) / _CARPETA_KEEL / "personas" / f"{nombre}.md"


def escribir_nota(ruta: Path, contenido: str, frontmatter: dict | None = None) -> None:
    """Crea o sobreescribe una nota Obsidian con frontmatter YAML."""
    ruta.parent.mkdir(parents=True, exist_ok=True)

    if frontmatter:
        fm_lines = ["---"]
        for k, v in frontmatter.items():
            if isinstance(v, list):
                fm_lines.append(f"{k}:")
                for item in v:
                    fm_lines.append(f"  - {item}")
            else:
                fm_lines.append(f"{k}: {v}")
        fm_lines.append("---\n")
        contenido = "\n".join(fm_lines) + contenido

    ruta.write_text(contenido, encoding="utf-8")


def exportar_reflexion(
    markdown: str,
    vault: str | None = None,
    fecha: str | None = None,
) -> Path:
    """Escribe el digest de reflexión como nota Obsidian."""
    f = fecha or date.today().isoformat()
    ruta = reflexion_path(vault, f)
    escribir_nota(
        ruta,
        markdown,
        frontmatter={
            "tipo": "reflexion-semanal",
            "fecha": f,
            "tags": ["keel", "reflexion", "relaciones"],
            "created": f,
        },
    )
    return ruta


def exportar_persona(persona, vault: str | None = None) -> Path:
    """Exporta el perfil de una persona como nota Obsidian."""
    from keel.models.persona import Persona
    assert isinstance(persona, Persona)

    ruta = persona_note_path(persona.nombre, vault)

    lineas = [f"# {persona.nombre}\n"]
    if persona.rol:
        lineas.append(f"**Rol:** {persona.rol}")
    if persona.como_nos_conocemos:
        lineas.append(f"**Cómo nos conocemos:** {persona.como_nos_conocemos}")
    if persona.tono_relacional:
        lineas.append(f"**Tono relacional:** {persona.tono_relacional}")
    if persona.sensibilidades:
        lineas.append(f"**Sensibilidades:** {', '.join(persona.sensibilidades)}")
    if persona.estado_actual:
        lineas.append(f"**Estado actual:** {persona.estado_actual}")
    lineas.append("")

    if persona.historial_conversaciones:
        lineas.append("## Conversaciones recientes\n")
        for conv in persona.historial_conversaciones[-10:]:
            temas = f" `{'`, `'.join(conv.temas)}`" if conv.temas else ""
            lineas.append(f"- **{conv.fecha}**{temas} — {conv.resumen}")
        lineas.append("")

    if persona.promesas_pendientes:
        lineas.append("## Compromisos pendientes\n")
        for pr in persona.promesas_pendientes:
            fecha = f" *(hasta {pr.fecha_compromiso})*" if pr.fecha_compromiso else ""
            lineas.append(f"- [ ] {pr.descripcion}{fecha}")
        lineas.append("")

    escribir_nota(
        ruta,
        "\n".join(lineas),
        frontmatter={
            "tipo": "persona-keel",
            "nombre": persona.nombre,
            "rol": persona.rol or "",
            "ultima_interaccion": persona.ultima_interaccion or "",
            "tags": ["keel", "persona", persona.nombre.lower()],
        },
    )
    return ruta


def agregar_a_diario(entrada: str, vault: str | None = None) -> Path:
    """Agrega una entrada al diario del día (crea la nota si no existe)."""
    ruta = daily_note_path(vault)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    hoy = date.today().isoformat()
    if not ruta.exists():
        escribir_nota(
            ruta,
            f"# Diario {hoy}\n\n",
            frontmatter={
                "fecha": hoy,
                "tags": ["diario", "keel"],
            },
        )

    contenido_actual = ruta.read_text(encoding="utf-8")
    ruta.write_text(contenido_actual + "\n" + entrada + "\n", encoding="utf-8")
    return ruta
