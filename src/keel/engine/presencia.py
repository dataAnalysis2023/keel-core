"""Capa Présence — detecta el tono emocional del mensaje entrante.

Análisis heurístico en el Hito 1. El Hito 2 puede reemplazar esto
por una llamada LLM dedicada cuando la latencia lo justifique.
"""

from dataclasses import dataclass


_INDICADORES: dict[str, list[str]] = {
    "urgente": ["urgente", "asap", "rápido", "ya", "inmediato", "necesito ahora", "lo antes posible"],
    "emocional": ["gracias", "increíble", "preocupa", "siento", "difícil", "tristeza", "alegría", "lamento", "feliz"],
    "formal": ["estimado", "cordialmente", "mediante", "presente", "atentamente", "le informo", "respetuosamente"],
    "tenso": ["no entiendo", "por qué", "decepcionado", "molesto", "no funciona", "inaceptable"],
}

# Umbral mínimo (fracción de indicadores detectados) para activar cada dimensión
_UMBRAL = 0.15


@dataclass
class ResultadoTono:
    urgencia: float     # 0–1
    emocionalidad: float
    formalidad: float
    tension: float
    resumen: str


def analizar_tono(mensaje: str) -> ResultadoTono:
    texto = mensaje.lower()

    scores: dict[str, float] = {}
    for dimension, palabras in _INDICADORES.items():
        hits = sum(1 for p in palabras if p in texto)
        scores[dimension] = min(hits / max(len(palabras) * 0.3, 1), 1.0)

    etiquetas: list[str] = []
    if scores["urgente"] > _UMBRAL:
        etiquetas.append("urgente")
    if scores["emocional"] > _UMBRAL:
        etiquetas.append("cargado emocionalmente")
    if scores["formal"] > _UMBRAL:
        etiquetas.append("formal")
    if scores["tenso"] > _UMBRAL:
        etiquetas.append("tenso")
    if not etiquetas:
        etiquetas.append("neutro y directo")

    return ResultadoTono(
        urgencia=scores["urgente"],
        emocionalidad=scores["emocional"],
        formalidad=scores["formal"],
        tension=scores["tenso"],
        resumen=", ".join(etiquetas),
    )
