"""Motor de aprendizaje: analiza historial de conversaciones y sugiere actualizaciones al perfil."""

import json
import re

from keel.llm.base import LLMBase
from keel.models.aprendizaje import SugerenciasPerfil
from keel.models.perfil import PerfilUsuario


def analizar_historial(
    perfil: PerfilUsuario,
    conversaciones: dict[str, list[str]],
    llm: LLMBase,
) -> SugerenciasPerfil:
    """Analiza conversaciones guardadas y sugiere qué agregar al perfil.

    Args:
        perfil: perfil actual del usuario (referencia para no repetir lo ya conocido)
        conversaciones: {nombre_persona: [resumen1, resumen2, ...]}
        llm: instancia LLM para el análisis
    """
    total = sum(len(v) for v in conversaciones.values())
    if total == 0:
        return SugerenciasPerfil(resumen="Sin historial suficiente para analizar.")

    prompt = _construir_prompt(perfil, conversaciones)
    respuesta = llm.generar(prompt)
    return _parsear_respuesta(respuesta)


def _construir_prompt(
    perfil: PerfilUsuario,
    conversaciones: dict[str, list[str]],
) -> str:
    frases = ", ".join(perfil.voz.frases_caracteristicas) or "ninguna registrada"
    vocabulario = ", ".join(perfil.voz.vocabulario_frecuente) or "ninguno registrado"
    valores = ", ".join(perfil.valores) or "ninguno registrado"

    bloques = []
    for persona, resumenes in conversaciones.items():
        if resumenes:
            lineas = "\n".join(f"  - {r}" for r in resumenes)
            bloques.append(f"Con {persona}:\n{lineas}")

    historial_texto = "\n\n".join(bloques)

    return f"""Analiza estas conversaciones guardadas por {perfil.nombre} y detecta patrones en su forma de comunicarse.

PERFIL ACTUAL (no repitas lo que ya está aquí):
- Frases características: {frases}
- Vocabulario frecuente: {vocabulario}
- Valores declarados: {valores}

HISTORIAL DE CONVERSACIONES:
{historial_texto}

Responde ÚNICAMENTE con un bloque JSON válido con esta estructura exacta:
{{
  "frases_nuevas": ["frase que usa con frecuencia y no está en el perfil"],
  "vocabulario_nuevo": ["término o expresión recurrente no registrado"],
  "valores_detectados": ["valor inferido del comportamiento, no declarado aún"],
  "temas_recurrentes": ["tema que aparece en múltiples conversaciones"],
  "resumen": "2-3 líneas describiendo los patrones más notorios"
}}

Incluye solo elementos con evidencia real en el historial. Si no hay suficiente evidencia para una categoría, devuelve lista vacía.
Solo JSON, sin texto adicional."""


def _parsear_respuesta(respuesta: str) -> SugerenciasPerfil:
    """Extrae JSON de la respuesta del LLM. Robusto ante texto adicional."""
    # Busca bloque JSON entre llaves
    match = re.search(r"\{[^{}]*\}", respuesta, re.DOTALL)
    if not match:
        return SugerenciasPerfil(resumen=f"No se pudo parsear la respuesta del LLM: {respuesta[:200]}")

    try:
        data = json.loads(match.group())
        return SugerenciasPerfil.model_validate(data)
    except (json.JSONDecodeError, Exception):
        return SugerenciasPerfil(resumen=f"Respuesta mal formada: {match.group()[:200]}")
