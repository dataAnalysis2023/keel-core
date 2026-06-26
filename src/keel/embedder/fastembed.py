"""Embedder local con FastEmbed — sin GPU, sin Ollama, multilingüe.

Primera vez que se usa descarga el modelo (~120MB) a ~/.cache/fastembed/.
Instancia singleton por modelo para no recargar en cada llamada.
"""

import warnings
from .base import EmbedderBase

# Modelo pequeño multilingüe, cubre español correctamente
MODELO_DEFAULT = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_instancias: dict[str, "FastEmbedder"] = {}


def get_embedder(modelo: str = MODELO_DEFAULT) -> "FastEmbedder":
    """Devuelve la instancia singleton para el modelo dado."""
    if modelo not in _instancias:
        _instancias[modelo] = FastEmbedder(modelo)
    return _instancias[modelo]


class FastEmbedder(EmbedderBase):
    def __init__(self, modelo: str = MODELO_DEFAULT):
        self.modelo = modelo
        self._modelo_interno = None
        self._dim: int | None = None

    def _cargar(self):
        if self._modelo_interno is None:
            from fastembed import TextEmbedding
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self._modelo_interno = TextEmbedding(model_name=self.modelo)
        return self._modelo_interno

    def embed(self, texto: str) -> list[float]:
        resultado = list(self._cargar().embed([texto]))[0]
        return resultado.tolist()

    def dimension(self) -> int:
        if self._dim is None:
            self._dim = len(self.embed("test"))
        return self._dim
