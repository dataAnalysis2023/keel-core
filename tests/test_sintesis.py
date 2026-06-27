"""Tests del motor de síntesis relacional — inferencia de narrativa y tipo de relación."""

import json
import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil, cargar_persona
from keel.engine.sintesis import (
    construir_prompt_sintesis,
    parsear_sintesis,
    sintetizar_persona,
    aplicar_sintesis,
    SintesisPersona,
    TIPOS_RELACION,
)

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
        tono_relacional="cercano",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-01-10", resumen="Kick-off del proyecto", temas=["producto"]),
            ConversacionResumen(fecha="2026-03-01", resumen="Demo con cliente", temas=["demo"]),
            ConversacionResumen(fecha="2026-05-15", resumen="Cierre Q1", temas=["legal"]),
            ConversacionResumen(fecha="2026-06-01", resumen="Revisión final de roadmap", temas=["producto"]),
        ],
    )


# ── construir_prompt_sintesis ─────────────────────────────────────────────────

def test_prompt_incluye_nombre_persona(persona_con_historial):
    prompt = construir_prompt_sintesis(persona_con_historial, "Juan")
    assert "Carlos" in prompt
    assert "Juan" in prompt


def test_prompt_incluye_historial(persona_con_historial):
    prompt = construir_prompt_sintesis(persona_con_historial, "Juan")
    assert "Kick-off" in prompt
    assert "Revisión final" in prompt


def test_prompt_incluye_rol(persona_con_historial):
    prompt = construir_prompt_sintesis(persona_con_historial, "Juan")
    assert "Director de Producto" in prompt


def test_prompt_incluye_tipos_relacion(persona_con_historial):
    prompt = construir_prompt_sintesis(persona_con_historial, "Juan")
    for tipo in TIPOS_RELACION:
        assert tipo in prompt


def test_prompt_limita_a_20_conversaciones():
    p = Persona(
        nombre="Ana",
        historial_conversaciones=[
            ConversacionResumen(fecha=f"2026-01-{i+1:02d}", resumen=f"Conv {i}")
            for i in range(25)
        ],
    )
    prompt = construir_prompt_sintesis(p, "Juan")
    # Solo las últimas 20 — "Conv 0" a "Conv 4" no deben aparecer
    assert "Conv 24" in prompt
    assert "Conv 0" not in prompt


def test_prompt_sin_promesas_no_incluye_seccion():
    p = Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Hola"),
    ])
    prompt = construir_prompt_sintesis(p, "Juan")
    assert "Compromisos pendientes" not in prompt


# ── parsear_sintesis ──────────────────────────────────────────────────────────

def test_parsear_json_limpio():
    raw = json.dumps({
        "narrativa": "Carlos es un colaborador clave.",
        "tipo_relacion": "trabajo",
        "contexto_situacional": "Lanzamiento de v2",
    })
    s = parsear_sintesis(raw)
    assert s.narrativa == "Carlos es un colaborador clave."
    assert s.tipo_relacion == "trabajo"
    assert s.contexto_situacional == "Lanzamiento de v2"


def test_parsear_json_con_ruido():
    raw = "Aquí está el JSON:\n" + json.dumps({
        "narrativa": "Relación profesional.",
        "tipo_relacion": "cliente",
        "contexto_situacional": "",
    }) + "\nEspero que ayude."
    s = parsear_sintesis(raw)
    assert s.narrativa == "Relación profesional."
    assert s.tipo_relacion == "cliente"


def test_parsear_tipo_invalido_normaliza_a_otro():
    raw = json.dumps({
        "narrativa": "Algo.",
        "tipo_relacion": "conocido_cercano",
    })
    s = parsear_sintesis(raw)
    assert s.tipo_relacion == "otro"


def test_parsear_json_invalido_usa_texto_como_narrativa():
    s = parsear_sintesis("no es json válido aquí")
    assert "no es json" in s.narrativa
    assert s.tipo_relacion == "otro"


def test_parsear_sin_contexto_situacional():
    raw = json.dumps({"narrativa": "Relación nueva.", "tipo_relacion": "nuevo"})
    s = parsear_sintesis(raw)
    assert s.contexto_situacional == ""


# ── sintetizar_persona + aplicar_sintesis ─────────────────────────────────────

def test_sintetizar_llama_llm_y_parsea(persona_con_historial):
    class FakeLLM:
        def generar(self, prompt):
            return json.dumps({
                "narrativa": "Carlos es un socio estratégico de largo plazo.",
                "tipo_relacion": "colaborador",
                "contexto_situacional": "Lanzamiento de producto Q2",
            })

    perfil = PerfilUsuario(nombre="Juan")
    s = sintetizar_persona(persona_con_historial, perfil, FakeLLM())
    assert s.tipo_relacion == "colaborador"
    assert "Carlos" in s.narrativa or "socio" in s.narrativa
    assert "Q2" in s.contexto_situacional


def test_aplicar_sintesis_actualiza_campos(persona_con_historial):
    from datetime import date
    s = SintesisPersona(
        narrativa="Relación de trabajo cercana.",
        tipo_relacion="trabajo",
        contexto_situacional="Campaña de lanzamiento",
    )
    aplicar_sintesis(persona_con_historial, s)
    assert persona_con_historial.narrativa == "Relación de trabajo cercana."
    assert persona_con_historial.tipo_relacion == "trabajo"
    assert persona_con_historial.contexto_situacional == "Campaña de lanzamiento"
    assert persona_con_historial.ultima_sintesis == date.today().isoformat()


def test_aplicar_sintesis_persiste(keel_tmp, persona_con_historial):
    guardar_persona(persona_con_historial)
    s = SintesisPersona(narrativa="Narrativa guardada.", tipo_relacion="cliente")
    aplicar_sintesis(persona_con_historial, s)
    guardar_persona(persona_con_historial)

    recargada = cargar_persona("Carlos")
    assert recargada.narrativa == "Narrativa guardada."
    assert recargada.tipo_relacion == "cliente"


# ── CLI keel persona sintetizar ───────────────────────────────────────────────

def test_cli_sintetizar_persona(keel_tmp, persona_con_historial, monkeypatch):
    import keel.llm.ollama as mod_ollama
    import keel.engine.sintesis as mod_sintesis

    guardar_persona(persona_con_historial)

    class FakeLLM:
        def __init__(self, **kw): pass
        def disponible(self): return True
        def generar(self, p):
            return json.dumps({
                "narrativa": "Carlos es colaborador estratégico.",
                "tipo_relacion": "colaborador",
                "contexto_situacional": "",
            })

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeLLM)

    result = runner.invoke(app, ["persona", "sintetizar", "Carlos"])
    assert result.exit_code == 0
    assert "colaborador" in result.output.lower() or "Carlos" in result.output

    p = cargar_persona("Carlos")
    assert p.narrativa != ""
    assert p.tipo_relacion == "colaborador"


def test_cli_sintetizar_todas(keel_tmp, persona_con_historial, monkeypatch):
    import keel.llm.ollama as mod_ollama

    guardar_persona(persona_con_historial)
    guardar_persona(Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha="2026-06-01", resumen="Primera llamada"),
    ]))

    class FakeLLM:
        def __init__(self, **kw): pass
        def disponible(self): return True
        def generar(self, p):
            return json.dumps({
                "narrativa": "Relación inferida.",
                "tipo_relacion": "trabajo",
                "contexto_situacional": "",
            })

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeLLM)

    result = runner.invoke(app, ["persona", "sintetizar"])
    assert result.exit_code == 0
    assert "2 persona" in result.output


def test_cli_sintetizar_sin_ollama(keel_tmp, persona_con_historial, monkeypatch):
    import keel.llm.ollama as mod_ollama

    guardar_persona(persona_con_historial)

    class FakeLLM:
        def __init__(self, **kw): pass
        def disponible(self): return False

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeLLM)

    result = runner.invoke(app, ["persona", "sintetizar", "Carlos"])
    assert result.exit_code != 0


def test_cli_sintetizar_persona_sin_historial(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama

    guardar_persona(Persona(nombre="Ana"))

    class FakeLLM:
        def __init__(self, **kw): pass
        def disponible(self): return True

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeLLM)

    result = runner.invoke(app, ["persona", "sintetizar", "Ana"])
    # Debe completar sin error pero indicar que se omitió
    assert result.exit_code == 0


# ── keel persona show muestra narrativa ──────────────────────────────────────

def test_show_muestra_narrativa(keel_tmp):
    p = Persona(
        nombre="Carlos",
        narrativa="Carlos es un colaborador de confianza.",
        tipo_relacion="colaborador",
    )
    guardar_persona(p)
    result = runner.invoke(app, ["persona", "show", "Carlos"])
    assert result.exit_code == 0
    assert "Carlos es un colaborador de confianza." in result.output
    assert "colaborador" in result.output


def test_show_sin_narrativa_no_muestra_panel(keel_tmp):
    guardar_persona(Persona(nombre="Ana"))
    result = runner.invoke(app, ["persona", "show", "Ana"])
    assert result.exit_code == 0
    assert "Síntesis relacional" not in result.output


# ── volcado incluye narrativa ─────────────────────────────────────────────────

def test_volcado_incluye_narrativa():
    from keel.engine.volcado import volcar_a_markdown
    perfil = PerfilUsuario(nombre="Juan")
    p = Persona(
        nombre="Carlos",
        narrativa="Colaborador estratégico desde el inicio.",
        tipo_relacion="colaborador",
        contexto_situacional="Lanzamiento de v2",
    )
    md = volcar_a_markdown(perfil, [p])
    assert "Colaborador estratégico" in md
    assert "Lanzamiento de v2" in md
    assert "colaborador" in md


def test_volcado_sin_narrativa_no_incluye_bloque():
    from keel.engine.volcado import volcar_a_markdown
    perfil = PerfilUsuario(nombre="Juan")
    p = Persona(nombre="Ana", rol="Abogada")
    md = volcar_a_markdown(perfil, [p])
    assert ">" not in md  # sin blockquote de narrativa
