"""Motor de síntesis relacional.

Infiere narrativa, tipo de relación y contexto situacional a partir
del historial de conversaciones — sin input explícito del usuario.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from keel.models.perfil import PerfilUsuario
    from keel.models.persona import Persona
    from keel.llm.base import LLMBase


TIPOS_RELACION = (
    "familia", "amistad", "trabajo", "cliente",
    "colaborador", "mentor", "nuevo", "otro",
)


class SintesisPersona(BaseModel):
    narrativa: str
    tipo_relacion: str = "otro"
    contexto_situacional: str = ""


def construir_prompt_sintesis(persona: "Persona", perfil_nombre: str) -> str:
    historial = persona.historial_conversaciones[-20:]  # últimas 20 entradas
    entradas = "\n".join(
        f"- {c.fecha}: {c.resumen}"
        + (f" [{', '.join(c.temas)}]" if c.temas else "")
        for c in historial
    ) or "(sin historial registrado)"

    promesas_str = ""
    if persona.promesas_pendientes:
        promesas_str = "\nCompromisos pendientes:\n" + "\n".join(
            f"- {p.descripcion}" + (f" (hasta {p.fecha_compromiso})" if p.fecha_compromiso else "")
            for p in persona.promesas_pendientes
        )

    meta = []
    if persona.rol:
        meta.append(f"Rol: {persona.rol}")
    if persona.tono_relacional and persona.tono_relacional != "neutro":
        meta.append(f"Tono observado: {persona.tono_relacional}")
    if persona.como_nos_conocemos:
        meta.append(f"Origen de la relación: {persona.como_nos_conocemos}")
    if persona.estado_actual:
        meta.append(f"Estado actual de la persona: {persona.estado_actual}")
    if persona.sensibilidades:
        meta.append(f"Sensibilidades: {', '.join(persona.sensibilidades)}")
    meta_str = ("\n".join(meta) + "\n") if meta else ""

    tipos = " | ".join(TIPOS_RELACION)

    return f"""Analiza el historial de interacciones entre {perfil_nombre} y {persona.nombre}.
Tu tarea es inferir el carácter real de esta relación a partir de los patrones observados.

{meta_str}Conversaciones registradas:
{entradas}
{promesas_str}

Responde ÚNICAMENTE con JSON válido, sin texto adicional:
{{
  "narrativa": "2-4 oraciones que describan quién es {persona.nombre} para {perfil_nombre}, la naturaleza real de la relación, patrones observados y dinámica actual",
  "tipo_relacion": "uno de: {tipos}",
  "contexto_situacional": "si hay un contexto coyuntural específico que explica el patrón de conversaciones (ej: lanzamiento de producto, campaña, crisis, colaboración puntual), descríbelo en 1 oración; si no hay contexto especial, deja el campo vacío"
}}"""


def parsear_sintesis(respuesta: str) -> SintesisPersona:
    """Extrae SintesisPersona del JSON de la respuesta LLM. Robusto ante ruido."""
    texto = respuesta.strip()
    # Extraer bloque JSON si viene envuelto en texto
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        texto = match.group(0)
    try:
        data = json.loads(texto)
        tipo = data.get("tipo_relacion", "otro").lower().strip()
        if tipo not in TIPOS_RELACION:
            tipo = "otro"
        return SintesisPersona(
            narrativa=data.get("narrativa", "").strip(),
            tipo_relacion=tipo,
            contexto_situacional=data.get("contexto_situacional", "").strip(),
        )
    except (json.JSONDecodeError, ValueError):
        # Fallback: usar la respuesta completa como narrativa
        return SintesisPersona(narrativa=texto[:400], tipo_relacion="otro")


def sintetizar_persona(
    persona: "Persona",
    perfil: "PerfilUsuario",
    llm: "LLMBase",
) -> SintesisPersona:
    """Infiere narrativa, tipo_relacion y contexto_situacional del historial."""
    prompt = construir_prompt_sintesis(persona, perfil.nombre)
    respuesta = llm.generar(prompt)
    return parsear_sintesis(respuesta)


def aplicar_sintesis(persona: "Persona", sintesis: SintesisPersona) -> "Persona":
    """Aplica los campos inferidos a la Persona y actualiza ultima_sintesis."""
    from datetime import date
    persona.narrativa = sintesis.narrativa
    persona.tipo_relacion = sintesis.tipo_relacion
    persona.contexto_situacional = sintesis.contexto_situacional
    persona.ultima_sintesis = date.today().isoformat()
    return persona
