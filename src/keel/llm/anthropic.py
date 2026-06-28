"""Implementación Anthropic — inferencia cloud vía SDK oficial."""

from __future__ import annotations

from .base import LLMBase

MODELO_DEFAULT = "claude-haiku-4-5-20251001"


class AnthropicLLM(LLMBase):
    def __init__(self, api_key: str, modelo: str = MODELO_DEFAULT) -> None:
        self._api_key = api_key
        self.modelo_default = modelo

    def generar(self, prompt: str, modelo: str | None = None) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "El SDK de Anthropic no está instalado. "
                "Ejecuta: pip install anthropic"
            ) from e

        client = anthropic.Anthropic(api_key=self._api_key)
        modelo_activo = modelo or self.modelo_default
        mensaje = client.messages.create(
            model=modelo_activo,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return mensaje.content[0].text

    def disponible(self) -> bool:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return bool(self._api_key)
