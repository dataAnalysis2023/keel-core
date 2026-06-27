"""Tests del ciclo autónomo nocturno — keel ciclo."""

import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil

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


def _persona(nombre, n_conv=3):
    p = Persona(nombre=nombre, historial_conversaciones=[
        ConversacionResumen(fecha=f"2026-01-{i+1:02d}", resumen=f"Conv {i}")
        for i in range(n_conv)
    ])
    guardar_persona(p)
    return p


def _fake_ollama_cls(disponible=True, respuesta=None):
    import json

    class FakeLLM:
        def __init__(self, **kw): pass
        def disponible(self): return disponible
        def generar(self, prompt):
            if respuesta:
                return respuesta
            return json.dumps({
                "narrativa": "Relación inferida automáticamente.",
                "tipo_relacion": "trabajo",
                "contexto_situacional": "",
            })

    return FakeLLM


# ── Comportamiento básico ─────────────────────────────────────────────────────

def test_ciclo_sintetiza_todas(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    _persona("Carlos")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo"])
    assert result.exit_code == 0
    assert "2 síntesis" in result.output

    from keel.storage.local import cargar_persona
    assert cargar_persona("Ana").narrativa != ""
    assert cargar_persona("Carlos").narrativa != ""


def test_ciclo_escribe_log(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    runner.invoke(app, ["ciclo"])
    log = keel_tmp / "logs" / "ciclo.log"
    assert log.exists()
    contenido = log.read_text()
    assert "Ciclo iniciado" in contenido
    assert "Ciclo completado" in contenido


def test_ciclo_log_incluye_tipo_relacion(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    runner.invoke(app, ["ciclo"])
    log = (keel_tmp / "logs" / "ciclo.log").read_text()
    assert "trabajo" in log  # tipo_relacion inferido


def test_ciclo_omite_personas_sin_historial(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    guardar_persona(Persona(nombre="Vacia"))
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo"])
    assert result.exit_code == 0
    assert "1 síntesis" in result.output


# ── Ollama no disponible — salida limpia ──────────────────────────────────────

def test_ciclo_ollama_no_disponible_sale_limpio(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls(disponible=False))

    result = runner.invoke(app, ["ciclo"])
    assert result.exit_code == 0  # salida limpia, launchd no marca error
    assert "pospuesto" in result.output.lower() or "no disponible" in result.output.lower()


def test_ciclo_ollama_no_disponible_registra_en_log(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls(disponible=False))

    runner.invoke(app, ["ciclo"])
    log = (keel_tmp / "logs" / "ciclo.log").read_text()
    assert "Ollama" in log or "pospuesto" in log.lower()


# ── --dry-run ─────────────────────────────────────────────────────────────────

def test_ciclo_dry_run_no_modifica(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo", "--dry-run"])
    assert result.exit_code == 0
    assert "dry" in result.output.lower() or "Ana" in result.output

    from keel.storage.local import cargar_persona
    assert cargar_persona("Ana").narrativa == ""  # no modificó


def test_ciclo_dry_run_registra_en_log(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    runner.invoke(app, ["ciclo", "--dry-run"])
    log = (keel_tmp / "logs" / "ciclo.log").read_text()
    assert "dry-run" in log.lower()


# ── --forzar ──────────────────────────────────────────────────────────────────

def test_ciclo_forzar_resinteza_hoy(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    from datetime import date
    p = _persona("Ana")
    p.ultima_sintesis = date.today().isoformat()
    p.narrativa = "Síntesis anterior"
    guardar_persona(p)

    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo", "--forzar"])
    assert result.exit_code == 0
    assert "1 síntesis" in result.output

    from keel.storage.local import cargar_persona
    nueva = cargar_persona("Ana")
    assert nueva.narrativa == "Relación inferida automáticamente."


def test_ciclo_sin_forzar_omite_sintetizadas_hoy(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    from datetime import date
    p = _persona("Ana")
    p.ultima_sintesis = date.today().isoformat()
    guardar_persona(p)

    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo"])
    assert result.exit_code == 0
    assert "Sin personas nuevas" in result.output


# ── --ver-log ─────────────────────────────────────────────────────────────────

def test_ver_log_sin_log_previo(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo", "--ver-log"])
    assert result.exit_code == 0
    assert "Sin log" in result.output


def test_ver_log_muestra_entradas(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    _persona("Ana")
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    runner.invoke(app, ["ciclo"])
    result = runner.invoke(app, ["ciclo", "--ver-log"])
    assert result.exit_code == 0
    assert "Ciclo" in result.output


# ── Sin perfil ────────────────────────────────────────────────────────────────

def test_ciclo_sin_perfil_falla(keel_tmp, monkeypatch):
    import keel.llm.ollama as mod_ollama
    (keel_tmp / "perfil.json").unlink()
    import keel.storage.local as sl
    monkeypatch.setattr(sl, "cargar_perfil", lambda: (_ for _ in ()).throw(FileNotFoundError("no hay perfil")))
    monkeypatch.setattr(mod_ollama, "OllamaLLM", _fake_ollama_cls())

    result = runner.invoke(app, ["ciclo"])
    assert result.exit_code != 0
