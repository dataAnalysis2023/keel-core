"""Tests de keel preparar — motor y CLI."""

import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil
from keel.engine.preparar import briefing_a_markdown, construir_prompt_briefing, _temas_frecuentes

runner = CliRunner()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    return keel


@pytest.fixture
def persona_completa():
    return Persona(
        nombre="Carlos",
        rol="Director de Producto",
        como_nos_conocemos="Cofundador de empresa anterior",
        tono_relacional="cercano",
        sensibilidades=["plazos", "burocracia"],
        estado_actual="lanzando nueva versión",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-01-10", resumen="Reunión de kick-off", temas=["producto", "roadmap"]),
            ConversacionResumen(fecha="2026-03-15", resumen="Revisión de avances", temas=["producto", "demo"]),
            ConversacionResumen(fecha="2026-05-20", resumen="Cierre de Q1", temas=["producto", "legal"]),
            ConversacionResumen(fecha="2026-06-01", resumen="Próxima demo", temas=["demo", "cliente"]),
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso="2026-07-01"),
        ],
        ultima_interaccion="2026-06-01",
    )


# ── Motor: briefing_a_markdown ────────────────────────────────────────────────

def test_briefing_incluye_nombre(persona_completa):
    md = briefing_a_markdown(persona_completa)
    assert "Carlos" in md


def test_briefing_incluye_rol(persona_completa):
    md = briefing_a_markdown(persona_completa)
    assert "Director de Producto" in md


def test_briefing_incluye_promesas(persona_completa):
    md = briefing_a_markdown(persona_completa)
    assert "Enviar propuesta" in md


def test_briefing_incluye_historial_reciente(persona_completa):
    md = briefing_a_markdown(persona_completa, n_recientes=2)
    assert "Próxima demo" in md
    assert "Cierre de Q1" in md
    # La más antigua NO debe aparecer con n_recientes=2
    assert "Reunión de kick-off" not in md


def test_briefing_incluye_sintesis(persona_completa):
    md = briefing_a_markdown(persona_completa, sintesis="Este es el resumen ejecutivo.")
    assert "Este es el resumen ejecutivo." in md


def test_briefing_sin_historial(keel_tmp):
    p = Persona(nombre="Ana")
    md = briefing_a_markdown(p)
    assert "Ana" in md
    assert "Últimas" not in md
    assert "Compromisos" not in md


def test_briefing_sensibilidades(persona_completa):
    md = briefing_a_markdown(persona_completa)
    assert "plazos" in md
    assert "burocracia" in md


def test_briefing_estado_actual(persona_completa):
    md = briefing_a_markdown(persona_completa)
    assert "lanzando nueva versión" in md


# ── Motor: temas frecuentes ───────────────────────────────────────────────────

def test_temas_frecuentes_extrae_top(persona_completa):
    temas = _temas_frecuentes(persona_completa)
    assert "producto" in temas  # aparece 3 veces
    assert "demo" in temas      # aparece 2 veces


def test_temas_frecuentes_excluye_unicos(persona_completa):
    temas = _temas_frecuentes(persona_completa)
    assert "legal" not in temas   # solo 1 vez
    assert "cliente" not in temas  # solo 1 vez


def test_temas_frecuentes_vacio():
    p = Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Hola")
    ])
    assert _temas_frecuentes(p) == []


# ── Motor: prompt_briefing ────────────────────────────────────────────────────

def test_prompt_incluye_nombre_perfil(persona_completa):
    prompt = construir_prompt_briefing(persona_completa, "Juan")
    assert "Juan" in prompt
    assert "Carlos" in prompt


def test_prompt_incluye_promesas(persona_completa):
    prompt = construir_prompt_briefing(persona_completa, "Juan")
    assert "Enviar propuesta" in prompt


def test_prompt_limita_recientes(persona_completa):
    prompt = construir_prompt_briefing(persona_completa, "Juan", n_recientes=2)
    assert "Próxima demo" in prompt
    assert "Reunión de kick-off" not in prompt


# ── CLI ────────────────────────────────────────────────────────────────────────

def test_preparar_sin_llm(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    result = runner.invoke(app, ["preparar", "--persona", "Carlos", "--sin-llm"])
    assert result.exit_code == 0
    assert "Carlos" in result.output
    assert "Enviar propuesta" in result.output


def test_preparar_persona_nueva(keel_tmp):
    """cargar_persona devuelve vacío si no existe — no debe fallar."""
    result = runner.invoke(app, ["preparar", "--persona", "Nadie", "--sin-llm"])
    assert result.exit_code == 0
    assert "Nadie" in result.output


def test_preparar_sin_perfil(keel_tmp):
    (keel_tmp / "perfil.json").unlink()
    result = runner.invoke(app, ["preparar", "--persona", "Carlos", "--sin-llm"])
    assert result.exit_code != 0


def test_preparar_recientes_limita(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    result = runner.invoke(app, ["preparar", "--persona", "Carlos", "--sin-llm", "--recientes", "1"])
    assert result.exit_code == 0
    assert "Próxima demo" in result.output
    assert "Reunión de kick-off" not in result.output


def test_preparar_clipboard(keel_tmp, persona_completa, monkeypatch):
    guardar_persona(persona_completa)
    escritos = []
    monkeypatch.setattr("keel.io.clipboard.escribir", lambda t: escritos.append(t))
    result = runner.invoke(app, ["preparar", "--persona", "Carlos", "--sin-llm", "--clipboard"])
    assert result.exit_code == 0
    assert len(escritos) == 1
    assert "Carlos" in escritos[0]


def test_preparar_usa_modelo_de_config(keel_tmp, persona_completa, monkeypatch):
    from keel.models.config import ConfigKeel
    from keel.storage.local import guardar_config
    guardar_persona(persona_completa)
    guardar_config(ConfigKeel(modelo_ollama="mi-modelo"))

    modelos_usados = []

    class FakeLLM:
        def __init__(self, modelo=None):
            modelos_usados.append(modelo)
        def disponible(self):
            return False

    monkeypatch.setattr("keel.cli.main.OllamaLLM" if hasattr(__import__('keel.cli.main', fromlist=['OllamaLLM']), 'OllamaLLM') else "keel.llm.ollama.OllamaLLM", FakeLLM, raising=False)

    import keel.llm.ollama as mod_ollama
    original = mod_ollama.OllamaLLM
    mod_ollama.OllamaLLM = FakeLLM

    runner.invoke(app, ["preparar", "--persona", "Carlos"])

    mod_ollama.OllamaLLM = original

    assert "mi-modelo" in modelos_usados
