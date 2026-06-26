"""Tests del almacenamiento vectorial — usa embedder falso para no depender de modelos."""

import pytest
import keel.storage.vectorial as mod_vectorial


class _EmbedderFalso:
    """Embedder determinista para tests — sin descargar modelos."""
    def embed(self, texto: str) -> list[float]:
        base = hash(texto) % 1000
        return [float(base + i) / 1000 for i in range(10)]

    def dimension(self) -> int:
        return 10


@pytest.fixture(autouse=False)
def keel_dir_tmp(tmp_path, monkeypatch):
    """Redirige _db_path a un directorio temporal durante el test."""
    db_tmp = tmp_path / "vectorial"
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: db_tmp)
    return db_tmp


def test_indexar_y_buscar(keel_dir_tmp):
    from keel.storage.vectorial import indexar_conversacion, buscar_similar

    embedder = _EmbedderFalso()
    indexar_conversacion("Carlos", "2026-06-01", "Hablamos del roadmap", ["roadmap"], embedder)
    indexar_conversacion("Carlos", "2026-06-10", "Revisamos el prototipo", ["prototipo"], embedder)

    resultados = buscar_similar("Carlos", "roadmap del producto", embedder, n=2)
    assert len(resultados) == 2
    assert all(r["persona"] == "Carlos" for r in resultados)


def test_buscar_sin_tabla_retorna_vacio(keel_dir_tmp):
    from keel.storage.vectorial import buscar_similar

    embedder = _EmbedderFalso()
    resultados = buscar_similar("Carlos", "cualquier cosa", embedder, n=3)
    assert resultados == []


def test_total_indexados(keel_dir_tmp):
    from keel.storage.vectorial import indexar_conversacion, total_indexados

    embedder = _EmbedderFalso()
    assert total_indexados() == 0

    indexar_conversacion("Carlos", "2026-06-01", "Primera nota", [], embedder)
    indexar_conversacion("María", "2026-06-02", "Segunda nota", [], embedder)

    assert total_indexados() == 2
    assert total_indexados("Carlos") == 1


def test_construir_prompt_usa_busqueda_semantica(keel_dir_tmp):
    from keel.storage.vectorial import indexar_conversacion
    from keel.engine.respuesta import construir_prompt
    from keel.models.perfil import PerfilUsuario
    from keel.models.persona import Persona

    embedder = _EmbedderFalso()
    indexar_conversacion("Carlos", "2026-06-01", "Discutimos el prototipo de Keel", ["keel"], embedder)

    perfil = PerfilUsuario(nombre="Juan")
    persona = Persona(nombre="Carlos")

    prompt = construir_prompt(perfil, persona, "¿Cómo va Keel?", "neutro", embedder)
    assert "semántica" in prompt or "Discutimos el prototipo" in prompt
