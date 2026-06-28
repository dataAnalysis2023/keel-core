"""Factory de LLM: instancia el proveedor configurado en ConfigKeel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import LLMBase

if TYPE_CHECKING:
    from keel.models.config import ConfigKeel


def crear_llm(config: "ConfigKeel", modelo_override: str | None = None) -> LLMBase:
    """Devuelve el LLM activo según config.proveedor.

    modelo_override sobreescribe el modelo para esta llamada puntual
    (equivalente al flag --modelo en CLI).
    """
    proveedor = config.proveedor

    if proveedor == "ollama":
        from keel.llm.ollama import OllamaLLM, MODELO_DEFAULT
        modelo = modelo_override or config.modelo_ollama or MODELO_DEFAULT
        return OllamaLLM(modelo=modelo)

    if proveedor == "anthropic":
        from keel.llm.anthropic import AnthropicLLM, MODELO_DEFAULT as ANT_DEFAULT
        from keel.security.api_keys import obtener_api_key
        key = obtener_api_key("anthropic")
        if not key:
            raise RuntimeError(
                "API key de Anthropic no configurada. "
                "Ejecuta: keel api-key set anthropic <tu-api-key>"
            )
        modelo = modelo_override or config.modelo_cloud or ANT_DEFAULT
        return AnthropicLLM(api_key=key, modelo=modelo)

    if proveedor == "openai":
        from keel.llm.openai_llm import OpenAILLM, MODELO_DEFAULT as OAI_DEFAULT
        from keel.security.api_keys import obtener_api_key
        key = obtener_api_key("openai")
        if not key:
            raise RuntimeError(
                "API key de OpenAI no configurada. "
                "Ejecuta: keel api-key set openai <tu-api-key>"
            )
        modelo = modelo_override or config.modelo_cloud or OAI_DEFAULT
        return OpenAILLM(api_key=key, modelo=modelo)

    raise ValueError(
        f"Proveedor '{proveedor}' desconocido. "
        "Opciones: ollama | anthropic | openai"
    )
