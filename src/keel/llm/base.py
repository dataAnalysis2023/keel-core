"""Interfaz abstracta para proveedores LLM.

Permite intercambiar Ollama por cualquier otro backend sin tocar el motor.
"""

from abc import ABC, abstractmethod


class LLMBase(ABC):
    @abstractmethod
    def generar(self, prompt: str, modelo: str | None = None) -> str: ...

    @abstractmethod
    def disponible(self) -> bool: ...
