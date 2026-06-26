"""Implementación Ollama — inferencia local."""

import httpx
from .base import LLMBase


OLLAMA_URL = "http://localhost:11434"
MODELO_DEFAULT = "qwen2.5-coder:7b"


class OllamaLLM(LLMBase):
    def __init__(self, url: str = OLLAMA_URL, modelo: str = MODELO_DEFAULT):
        self.url = url
        self.modelo_default = modelo

    def generar(self, prompt: str, modelo: str | None = None) -> str:
        modelo_activo = modelo or self.modelo_default
        payload = {"model": modelo_activo, "prompt": prompt, "stream": False}
        try:
            resp = httpx.post(
                f"{self.url}/api/generate",
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            return resp.json()["response"]
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"No se pudo conectar a Ollama en {self.url}. "
                "Verifica que esté corriendo: `ollama serve`"
            ) from e

    def disponible(self) -> bool:
        try:
            resp = httpx.get(f"{self.url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def modelos_disponibles(self) -> list[str]:
        try:
            resp = httpx.get(f"{self.url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            return []
