"""Interfaz abstracta para proveedores de embeddings.

Separado de LLMBase porque generación y vectorización son responsabilidades
distintas — se pueden usar modelos diferentes para cada una.
"""

from abc import ABC, abstractmethod


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texto: str) -> list[float]: ...

    @abstractmethod
    def dimension(self) -> int: ...
