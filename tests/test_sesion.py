"""Tests de keel.engine.sesion — sin TTY, sin Ollama."""

import json
import pytest
import keel.storage.vectorial as mod_vectorial

from keel.engine.sesion import (
    generar_resumen_automatico,
    guardar,
    ResultadoSesion,
)
from keel.engine.presencia import ResultadoTono
from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr("keel.storage.local._KEEL_DIR", keel)
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: keel / "vectorial")
    return keel


# ── generar_resumen_automatico ────────────────────────────────────────────────

def test_resumen_mensaje_corto():
    resumen = generar_resumen_automatico("Hola, ¿cómo estás?", "Bien, gracias")
    assert resumen == "Hola, ¿cómo estás?"


def test_resumen_mensaje_largo():
    largo = "x" * 100
    resumen = generar_resumen_automatico(largo, "")
    assert resumen.endswith("…")
    assert len(resumen) <= 81


def test_resumen_limpia_saltos():
    resumen = generar_resumen_automatico("Primera línea\nSegunda línea", "")
    assert "\n" not in resumen


# ── guardar ───────────────────────────────────────────────────────────────────

def test_guardar_agrega_al_historial(keel_tmp):
    persona = Persona(nombre="María")
    assert len(persona.historial_conversaciones) == 0

    guardar(persona, "Hablamos del roadmap", ["roadmap"], embedder=None)

    assert len(persona.historial_conversaciones) == 1
    assert persona.historial_conversaciones[0].resumen == "Hablamos del roadmap"
    assert persona.ultima_interaccion is not None


def test_guardar_persiste_en_disco(keel_tmp):
    from keel.storage.local import cargar_persona

    persona = Persona(nombre="Luis")
    guardar(persona, "Primera nota", ["test"], embedder=None)

    reloaded = cargar_persona("Luis")
    assert len(reloaded.historial_conversaciones) == 1
    assert reloaded.historial_conversaciones[0].resumen == "Primera nota"


def test_guardar_multiples_sesiones(keel_tmp):
    from keel.storage.local import cargar_persona

    persona = Persona(nombre="Pedro")
    guardar(persona, "Primera sesión", [], None)

    # La segunda sesión siempre carga del disco antes de guardar
    persona2 = cargar_persona("Pedro")
    guardar(persona2, "Segunda sesión", ["proyecto"], None)

    final = cargar_persona("Pedro")
    assert len(final.historial_conversaciones) == 2


def test_guardar_indexa_con_embedder(keel_tmp):
    from keel.storage.vectorial import total_indexados

    class _EmbedderFalso:
        def embed(self, t): return [float(hash(t) % 1000) / 1000 for _ in range(10)]
        def dimension(self): return 10

    persona = Persona(nombre="Ana")
    guardar(persona, "Hablamos de lanzamiento", ["lanzamiento"], _EmbedderFalso())

    assert total_indexados("Ana") == 1


# ── ejecutar (mock LLM) ───────────────────────────────────────────────────────

def test_ejecutar_modo_sin_historial():
    from keel.engine.sesion import ejecutar

    class _LLMFalso:
        def generar(self, prompt, modelo=None): return "Respuesta de prueba"
        def disponible(self): return True

    perfil = PerfilUsuario(nombre="Juan")
    persona = Persona(nombre="Carlos")

    resultado = ejecutar(perfil, persona, "Hola, ¿cómo estás?", _LLMFalso())

    assert resultado.sugerencia == "Respuesta de prueba"
    assert resultado.modo_contexto == "sin historial"


def test_ejecutar_modo_cronologico():
    from keel.engine.sesion import ejecutar
    from keel.models.persona import ConversacionResumen

    class _LLMFalso:
        def generar(self, prompt, modelo=None): return "OK"
        def disponible(self): return True

    perfil = PerfilUsuario(nombre="Juan")
    persona = Persona(
        nombre="María",
        historial_conversaciones=[ConversacionResumen(fecha="2026-06-01", resumen="Algo")]
    )

    resultado = ejecutar(perfil, persona, "Hola", _LLMFalso())
    assert resultado.modo_contexto == "cronológico"


def test_ejecutar_modo_semantico():
    from keel.engine.sesion import ejecutar

    class _LLMFalso:
        def generar(self, prompt, modelo=None): return "OK"
        def disponible(self): return True

    class _EmbedderFalso:
        def embed(self, t): return [0.1] * 10
        def dimension(self): return 10

    perfil = PerfilUsuario(nombre="Juan")
    persona = Persona(nombre="Pedro")

    resultado = ejecutar(perfil, persona, "Hola", _LLMFalso(), _EmbedderFalso())
    assert resultado.modo_contexto == "semántico"
