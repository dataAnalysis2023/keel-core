"""Tests de keel pregunta — motor y CLI."""

import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil
from keel.engine.pregunta import construir_prompt_pregunta, respuesta_sin_llm

runner = CliRunner(env={"COLUMNS": "200"})
_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    return keel


@pytest.fixture
def persona_con_historial():
    return Persona(
        nombre="Carlos",
        rol="Director de Producto",
        estado_actual="lanzando nueva versión",
        tono_relacional="cercano",
        historial_conversaciones=[
            ConversacionResumen(
                fecha="2026-03-01",
                resumen="Acordamos entregar el prototipo en abril",
                temas=["prototipo", "entrega"],
            ),
            ConversacionResumen(
                fecha="2026-04-15",
                resumen="Revisión del cliente final con feedback positivo",
                temas=["cliente", "feedback"],
            ),
            ConversacionResumen(
                fecha="2026-05-10",
                resumen="Se pospuso el lanzamiento a junio por temas legales",
                temas=["lanzamiento", "legal"],
            ),
        ],
    )


# ── construir_prompt_pregunta ──────────────────────────────────────────────────

def test_prompt_incluye_pregunta(persona_con_historial):
    p = construir_prompt_pregunta(
        "¿qué acordamos sobre el prototipo?",
        persona_con_historial,
        "Juan",
        [],
    )
    assert "¿qué acordamos sobre el prototipo?" in p


def test_prompt_incluye_nombre_persona(persona_con_historial):
    p = construir_prompt_pregunta("pregunta", persona_con_historial, "Juan", [])
    assert "Carlos" in p


def test_prompt_incluye_perfil(persona_con_historial):
    p = construir_prompt_pregunta("pregunta", persona_con_historial, "Juan", [])
    assert "Juan" in p


def test_prompt_con_contexto_incluye_fragmentos(persona_con_historial):
    contexto = [
        {"fecha": "2026-03-01", "resumen": "Acordamos entregar en abril", "temas": ["prototipo"]},
    ]
    p = construir_prompt_pregunta("pregunta", persona_con_historial, "Juan", contexto)
    assert "2026-03-01" in p
    assert "Acordamos entregar en abril" in p
    assert "prototipo" in p


def test_prompt_sin_contexto_lo_indica(persona_con_historial):
    p = construir_prompt_pregunta("pregunta", persona_con_historial, "Juan", [])
    assert "no se encontraron" in p.lower()


def test_prompt_incluye_rol_y_estado(persona_con_historial):
    p = construir_prompt_pregunta("pregunta", persona_con_historial, "Juan", [])
    assert "Director de Producto" in p
    assert "lanzando nueva versión" in p


def test_prompt_sin_rol_no_falla():
    p_simple = Persona(nombre="Ana")
    prompt = construir_prompt_pregunta("pregunta", p_simple, "Juan", [])
    assert "Ana" in prompt


# ── respuesta_sin_llm ─────────────────────────────────────────────────────────

def test_respuesta_sin_llm_sin_contexto():
    r = respuesta_sin_llm([], "Carlos")
    assert "Carlos" in r
    assert "no hay historial" in r.lower()


def test_respuesta_sin_llm_con_contexto():
    contexto = [
        {"fecha": "2026-03-01", "resumen": "Reunión kick-off", "temas": ["producto"]},
        {"fecha": "2026-04-01", "resumen": "Demo al cliente", "temas": []},
    ]
    r = respuesta_sin_llm(contexto, "Carlos")
    assert "Carlos" in r
    assert "Reunión kick-off" in r
    assert "Demo al cliente" in r
    assert "2026-03-01" in r


def test_respuesta_sin_llm_temas_opcionales():
    contexto = [{"fecha": "2026-01-01", "resumen": "Sin temas", "temas": []}]
    r = respuesta_sin_llm(contexto, "Ana")
    assert "Sin temas" in r


# ── modo global (sin --persona) ────────────────────────────────────────────────

def test_prompt_global_sin_persona():
    p = construir_prompt_pregunta("¿quién habló del proyecto?", None, "Juan", [])
    assert "relaciones personales" in p.lower()
    assert "Juan" in p


def test_prompt_global_con_contexto_incluye_nombre_persona():
    contexto = [
        {"persona": "Carlos", "fecha": "2026-03-01", "resumen": "Habló del proyecto", "temas": ["proyecto"]},
        {"persona": "Ana", "fecha": "2026-04-01", "resumen": "Revisó el contrato", "temas": ["legal"]},
    ]
    p = construir_prompt_pregunta("¿quién habló del proyecto?", None, "Juan", contexto)
    assert "Carlos" in p
    assert "Ana" in p


def test_respuesta_sin_llm_global_sin_contexto():
    r = respuesta_sin_llm([], None)
    assert "no hay historial" in r.lower()


def test_respuesta_sin_llm_global_muestra_persona():
    contexto = [
        {"persona": "Carlos", "fecha": "2026-01-01", "resumen": "Proyecto X", "temas": []},
    ]
    r = respuesta_sin_llm(contexto, None)
    assert "Carlos" in r
    assert "Proyecto X" in r


def test_cli_global_sin_personas(keel_tmp):
    result = runner.invoke(app, ["pregunta", "¿algo?", "--sin-llm"])
    assert result.exit_code == 0
    assert "No hay personas" in result.output


def test_cli_global_busca_en_todas(keel_tmp, persona_con_historial, monkeypatch):
    guardar_persona(persona_con_historial)
    ana = Persona(
        nombre="Ana",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-05-01", resumen="Reunión legal importante", temas=["legal"]),
        ],
    )
    guardar_persona(ana)
    result = runner.invoke(app, ["pregunta", "legal", "--sin-llm", "--sin-vectores"])
    assert result.exit_code == 0
    assert "legal" in result.output.lower() or "Ana" in result.output


def test_cli_global_llm_mockeado(keel_tmp, persona_con_historial, monkeypatch):
    guardar_persona(persona_con_historial)
    import keel.llm.ollama as mod_ollama

    class FakeOllama:
        def __init__(self, **kw): pass
        def disponible(self): return True
        def generar(self, prompt): return "Respuesta global."

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeOllama)
    result = runner.invoke(app, ["pregunta", "prototipo", "--sin-vectores"])
    assert result.exit_code == 0
    assert "Respuesta global." in result.output


# ── CLI --sin-llm ─────────────────────────────────────────────────────────────

def test_cli_sin_llm_persona_sin_historial(keel_tmp):
    guardar_persona(Persona(nombre="Ana"))
    result = runner.invoke(app, ["pregunta", "¿qué hablamos?", "--persona", "Ana", "--sin-llm"])
    assert result.exit_code == 0
    assert "no hay historial" in result.output.lower()


def test_cli_sin_llm_muestra_fragmentos(keel_tmp, persona_con_historial):
    guardar_persona(persona_con_historial)
    result = runner.invoke(
        app,
        ["pregunta", "prototipo", "--persona", "Carlos", "--sin-llm", "--sin-vectores"],
    )
    assert result.exit_code == 0
    assert "Carlos" in result.output


def test_cli_sin_llm_persona_inexistente_crea_vacia(keel_tmp):
    result = runner.invoke(app, ["pregunta", "algo", "--persona", "Nadie", "--sin-llm"])
    assert result.exit_code == 0
    assert "no hay historial" in result.output.lower()


# ── CLI con LLM mockeado ──────────────────────────────────────────────────────

def test_cli_llm_no_disponible_fallback(keel_tmp, persona_con_historial, monkeypatch):
    guardar_persona(persona_con_historial)
    import keel.llm.ollama as mod_ollama

    class FakeOllama:
        def __init__(self, **kw): pass
        def disponible(self): return False
        def generar(self, prompt): return ""

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeOllama)
    result = runner.invoke(
        app,
        ["pregunta", "¿qué acordamos?", "--persona", "Carlos", "--sin-vectores"],
    )
    assert result.exit_code == 0
    assert "Ollama no disponible" in result.output


def test_cli_llm_disponible_genera_respuesta(keel_tmp, persona_con_historial, monkeypatch):
    guardar_persona(persona_con_historial)
    import keel.llm.ollama as mod_ollama

    class FakeOllama:
        def __init__(self, **kw): pass
        def disponible(self): return True
        def generar(self, prompt): return "Acordaron entregar el prototipo en abril."

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeOllama)
    result = runner.invoke(
        app,
        ["pregunta", "¿qué acordamos sobre el prototipo?", "--persona", "Carlos", "--sin-vectores"],
    )
    assert result.exit_code == 0
    assert "Acordaron entregar el prototipo en abril." in result.output


def test_cli_sin_perfil_lanza_error(keel_tmp, monkeypatch):
    import keel.storage.local as sl
    original = sl.cargar_perfil
    def _fail(): raise FileNotFoundError("no hay perfil")
    monkeypatch.setattr(sl, "cargar_perfil", _fail)

    result = runner.invoke(app, ["pregunta", "algo", "--persona", "Ana", "--sin-llm"])
    assert result.exit_code != 0
