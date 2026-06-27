"""Tests de keel hoy — resumen diario de actividad."""

import pytest
from datetime import date, timedelta
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.storage.local import guardar_persona

runner = CliRunner()
HOY = date.today().isoformat()
AYER = (date.today() - timedelta(days=1)).isoformat()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


# ── Sin actividad ─────────────────────────────────────────────────────────────

def test_hoy_sin_personas(keel_tmp):
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Sin actividad" in result.output


def test_hoy_sin_actividad_hoy(keel_tmp):
    guardar_persona(Persona(nombre="Carlos", historial_conversaciones=[
        ConversacionResumen(fecha=AYER, resumen="Conversación de ayer", temas=[]),
    ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Sin actividad" in result.output


# ── Conversaciones de hoy ─────────────────────────────────────────────────────

def test_hoy_muestra_conversaciones(keel_tmp):
    guardar_persona(Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha=HOY, resumen="Reunión de producto", temas=["producto", "demo"]),
    ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Ana" in result.output
    assert "Reunión de producto" in result.output
    assert "producto" in result.output


def test_hoy_multiples_personas(keel_tmp):
    for nombre, resumen in [("Ana", "Kick-off"), ("Carlos", "Cierre de contrato")]:
        guardar_persona(Persona(nombre=nombre, historial_conversaciones=[
            ConversacionResumen(fecha=HOY, resumen=resumen, temas=[]),
        ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Ana" in result.output
    assert "Carlos" in result.output
    assert "Kick-off" in result.output
    assert "Cierre de contrato" in result.output


def test_hoy_ignora_otras_fechas(keel_tmp):
    guardar_persona(Persona(nombre="Luis", historial_conversaciones=[
        ConversacionResumen(fecha=HOY, resumen="Hoy", temas=[]),
        ConversacionResumen(fecha=AYER, resumen="Ayer — no debe aparecer", temas=[]),
    ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Hoy" in result.output
    assert "Ayer — no debe aparecer" not in result.output


# ── Promesas con fecha hoy ────────────────────────────────────────────────────

def test_hoy_muestra_promesas_con_fecha_hoy(keel_tmp):
    guardar_persona(Persona(nombre="Pedro", promesas_pendientes=[
        PromesaPendiente(descripcion="Entregar informe", fecha_compromiso=HOY),
        PromesaPendiente(descripcion="Otra para más tarde", fecha_compromiso="2026-12-01"),
    ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "Entregar informe" in result.output
    assert "Otra para más tarde" not in result.output


# ── Filtro de fecha ───────────────────────────────────────────────────────────

def test_hoy_con_fecha_especifica(keel_tmp):
    guardar_persona(Persona(nombre="María", historial_conversaciones=[
        ConversacionResumen(fecha="2026-05-10", resumen="Reunión histórica", temas=[]),
    ]))
    result = runner.invoke(app, ["hoy", "--fecha", "2026-05-10"])
    assert result.exit_code == 0
    assert "Reunión histórica" in result.output
    assert "2026-05-10" in result.output


def test_hoy_fecha_invalida(keel_tmp):
    result = runner.invoke(app, ["hoy", "--fecha", "no-es-fecha"])
    assert result.exit_code != 0


# ── Resumen ───────────────────────────────────────────────────────────────────

def test_hoy_muestra_conteo(keel_tmp):
    guardar_persona(Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha=HOY, resumen="Conv 1", temas=[]),
        ConversacionResumen(fecha=HOY, resumen="Conv 2", temas=[]),
    ]))
    result = runner.invoke(app, ["hoy"])
    assert result.exit_code == 0
    assert "2 conversación" in result.output


# ── Clipboard ─────────────────────────────────────────────────────────────────

def test_hoy_clipboard(keel_tmp, monkeypatch):
    guardar_persona(Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha=HOY, resumen="Demo con cliente", temas=["demo"]),
    ]))
    escritos = []
    monkeypatch.setattr("keel.io.clipboard.escribir", lambda t: escritos.append(t))
    result = runner.invoke(app, ["hoy", "--clipboard"])
    assert result.exit_code == 0
    assert len(escritos) == 1
    assert "Demo con cliente" in escritos[0]
