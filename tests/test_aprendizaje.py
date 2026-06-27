"""Tests de keel.engine.aprendizaje."""

import json
import pytest

from keel.engine.aprendizaje import analizar_historial, _construir_prompt, _parsear_respuesta
from keel.models.aprendizaje import SugerenciasPerfil
from keel.models.perfil import PerfilUsuario, VozUsuario


class _LLMFalso:
    def __init__(self, respuesta: str):
        self._respuesta = respuesta

    def generar(self, prompt, modelo=None):
        return self._respuesta

    def disponible(self):
        return True


@pytest.fixture
def perfil_base():
    return PerfilUsuario(
        nombre="Juan",
        voz=VozUsuario(
            tono="directo",
            frases_caracteristicas=["vamos al punto"],
            vocabulario_frecuente=["ecosistema"],
        ),
        valores=["claridad", "impacto"],
    )


# ── analizar_historial ────────────────────────────────────────────────────────

def test_sin_historial_retorna_resumen_vacio(perfil_base):
    llm = _LLMFalso("{}")
    resultado = analizar_historial(perfil_base, {}, llm)
    assert "Sin historial" in resultado.resumen


def test_historial_vacio_en_personas(perfil_base):
    llm = _LLMFalso("{}")
    resultado = analizar_historial(perfil_base, {"Carlos": []}, llm)
    assert "Sin historial" in resultado.resumen


def test_llm_recibe_prompt_con_perfil(perfil_base):
    prompts_recibidos = []

    class _LLMCaptura:
        def generar(self, prompt, modelo=None):
            prompts_recibidos.append(prompt)
            return '{"frases_nuevas": [], "vocabulario_nuevo": [], "valores_detectados": [], "temas_recurrentes": [], "resumen": "ok"}'
        def disponible(self): return True

    analizar_historial(perfil_base, {"María": ["Hablamos del roadmap"]}, _LLMCaptura())
    assert "vamos al punto" in prompts_recibidos[0]
    assert "claridad" in prompts_recibidos[0]
    assert "María" in prompts_recibidos[0]


def test_sugerencias_completas_parseadas(perfil_base):
    respuesta_llm = json.dumps({
        "frases_nuevas": ["¿qué implica esto?", "bien, sigamos"],
        "vocabulario_nuevo": ["protocolo", "trazabilidad"],
        "valores_detectados": ["autonomía"],
        "temas_recurrentes": ["producto", "automatización"],
        "resumen": "Juan usa lenguaje sistémico con frecuencia.",
    })
    llm = _LLMFalso(respuesta_llm)
    resultado = analizar_historial(perfil_base, {"Carlos": ["Hablamos de producto"]}, llm)

    assert "¿qué implica esto?" in resultado.frases_nuevas
    assert "protocolo" in resultado.vocabulario_nuevo
    assert "autonomía" in resultado.valores_detectados
    assert "producto" in resultado.temas_recurrentes
    assert resultado.resumen


# ── _parsear_respuesta ────────────────────────────────────────────────────────

def test_parsear_json_puro():
    raw = '{"frases_nuevas": ["hola"], "vocabulario_nuevo": [], "valores_detectados": [], "temas_recurrentes": [], "resumen": "test"}'
    s = _parsear_respuesta(raw)
    assert s.frases_nuevas == ["hola"]


def test_parsear_json_con_texto_adicional():
    raw = 'Aquí el análisis:\n{"frases_nuevas": ["ok"], "vocabulario_nuevo": [], "valores_detectados": [], "temas_recurrentes": [], "resumen": "x"}\nEspero que ayude.'
    s = _parsear_respuesta(raw)
    assert s.frases_nuevas == ["ok"]


def test_parsear_sin_json_devuelve_fallback():
    s = _parsear_respuesta("No pude generar el análisis solicitado.")
    assert isinstance(s, SugerenciasPerfil)
    assert "No se pudo parsear" in s.resumen


def test_parsear_json_malformado_devuelve_fallback():
    s = _parsear_respuesta("{frases_nuevas: broken json}")
    assert isinstance(s, SugerenciasPerfil)


# ── _construir_prompt ─────────────────────────────────────────────────────────

def test_prompt_incluye_nombre_y_persona(perfil_base):
    prompt = _construir_prompt(perfil_base, {"Luis": ["Cerramos el trato"]})
    assert "Juan" in prompt
    assert "Luis" in prompt
    assert "Cerramos el trato" in prompt


def test_prompt_excluye_valores_ya_en_perfil(perfil_base):
    prompt = _construir_prompt(perfil_base, {"Ana": ["Algo"]})
    assert "no repitas" in prompt.lower() or "no está en el perfil" in prompt.lower() or "no declarado" in prompt.lower()
