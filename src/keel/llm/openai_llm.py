"""Implementación OpenAI — inferencia cloud vía SDK oficial."""

from __future__ import annotations

from .base import LLMBase

MODELO_DEFAULT = "gpt-4o-mini"


class OpenAILLM(LLMBase):
    def __init__(self, api_key: str, modelo: str = MODELO_DEFAULT) -> None:
        self._api_key = api_key
        self.modelo_default = modelo

    def generar(self, prompt: str, modelo: str | None = None) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "El SDK de OpenAI no está instalado. "
                "Ejecuta: pip install openai"
            ) from e

        client = OpenAI(api_key=self._api_key)
        modelo_activo = modelo or self.modelo_default
        resp = client.chat.completions.create(
            model=modelo_activo,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""

    def disponible(self) -> bool:
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            return False
        return bool(self._api_key)
