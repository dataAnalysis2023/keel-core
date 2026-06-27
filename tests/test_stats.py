"""Tests de keel stats — motor y CLI."""

import json
import pytest
from datetime import date, timedelta
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.storage.local import guardar_persona
from keel.engine.stats import calcular_stats, _personas_activas, _temas_frecuentes, _por_mes, _promesas_vencidas

runner = CliRunner()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


@pytest.fixture
def personas_fixture():
    hoy = date.today()
    vencida = (hoy - timedelta(days=5)).isoformat()
    futura = (hoy + timedelta(days=10)).isoformat()

    return [
        Persona(
            nombre="Carlos",
            historial_conversaciones=[
                ConversacionResumen(fecha="2026-01-10", resumen="R1", temas=["producto", "roadmap"]),
                ConversacionResumen(fecha="2026-01-20", resumen="R2", temas=["producto"]),
                ConversacionResumen(fecha="2026-03-05", resumen="R3", temas=["legal"]),
            ],
            promesas_pendientes=[
                PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso=vencida),
                PromesaPendiente(descripcion="Llamar cliente", fecha_compromiso=futura),
            ],
            ultima_interaccion="2026-03-05",
        ),
        Persona(
            nombre="Ana",
            historial_conversaciones=[
                ConversacionResumen(fecha="2026-02-15", resumen="Reunión", temas=["producto", "demo"]),
                ConversacionResumen(fecha="2026-03-01", resumen="Demo", temas=["demo"]),
            ],
            ultima_interaccion="2026-03-01",
        ),
        Persona(nombre="Luis"),  # sin historial
    ]


# ── Motor: calcular_stats ─────────────────────────────────────────────────────

def test_stats_totales(personas_fixture):
    s = calcular_stats(personas_fixture)
    assert s["total_personas"] == 3
    assert s["total_conversaciones"] == 5
    assert s["total_promesas_pendientes"] == 2


def test_stats_sin_historial(personas_fixture):
    s = calcular_stats(personas_fixture)
    assert "Luis" in s["sin_historial"]
    assert "Carlos" not in s["sin_historial"]


def test_personas_activas_orden(personas_fixture):
    activas = _personas_activas(personas_fixture)
    assert activas[0]["nombre"] == "Carlos"  # 3 conversaciones
    assert activas[1]["nombre"] == "Ana"      # 2 conversaciones


def test_personas_activas_excluye_sin_historial(personas_fixture):
    activas = _personas_activas(personas_fixture)
    nombres = [d["nombre"] for d in activas]
    assert "Luis" not in nombres


def test_temas_frecuentes_orden(personas_fixture):
    temas = _temas_frecuentes(personas_fixture)
    nombres = [d["tema"] for d in temas]
    assert nombres[0] == "producto"  # 3 menciones
    assert "demo" in nombres          # 2 menciones


def test_temas_frecuentes_limita_top(personas_fixture):
    temas = _temas_frecuentes(personas_fixture, top=2)
    assert len(temas) <= 2


def test_por_mes(personas_fixture):
    por_mes = _por_mes(personas_fixture)
    assert "2026-01" in por_mes
    assert por_mes["2026-01"] == 2
    assert por_mes["2026-03"] == 2


def test_promesas_vencidas(personas_fixture):
    s = calcular_stats(personas_fixture)
    assert len(s["promesas_vencidas"]) == 1
    assert s["promesas_vencidas"][0]["persona"] == "Carlos"
    assert s["promesas_vencidas"][0]["descripcion"] == "Enviar propuesta"
    assert s["promesas_vencidas"][0]["dias_vencida"] == 5


def test_stats_sin_personas():
    s = calcular_stats([])
    assert s["total_personas"] == 0
    assert s["total_conversaciones"] == 0
    assert s["personas_activas"] == []
    assert s["temas_frecuentes"] == []


# ── CLI ────────────────────────────────────────────────────────────────────────

def test_stats_cli_muestra_resumen(keel_tmp, personas_fixture):
    for p in personas_fixture:
        guardar_persona(p)
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "3" in result.output  # total_personas
    assert "Carlos" in result.output
    assert "producto" in result.output


def test_stats_cli_json(keel_tmp, personas_fixture):
    for p in personas_fixture:
        guardar_persona(p)
    result = runner.invoke(app, ["stats", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total_personas"] == 3
    assert data["total_conversaciones"] == 5
    assert isinstance(data["temas_frecuentes"], list)


def test_stats_cli_sin_personas(keel_tmp):
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "No hay personas" in result.output


def test_stats_cli_muestra_vencidas(keel_tmp, personas_fixture):
    for p in personas_fixture:
        guardar_persona(p)
    result = runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "vencida" in result.output.lower() or "Enviar propuesta" in result.output
