"""Tests de keel historial."""

import json
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen
from keel.storage.local import guardar_persona

runner = CliRunner()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


@pytest.fixture
def persona_con_historial(keel_tmp):
    p = Persona(
        nombre="Carlos",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-01-10", resumen="Reunión de kick-off", temas=["proyecto"]),
            ConversacionResumen(fecha="2026-03-15", resumen="Revisión de avances", temas=["producto", "demo"]),
            ConversacionResumen(fecha="2026-05-20", resumen="Cierre de contrato", temas=["legal", "contrato"]),
            ConversacionResumen(fecha="2026-06-01", resumen="Llamada de seguimiento", temas=[]),
        ],
        ultima_interaccion="2026-06-01",
    )
    guardar_persona(p)
    return p


# ── Básico ─────────────────────────────────────────────────────────────────────

def test_historial_muestra_entradas(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos"])
    assert result.exit_code == 0
    assert "Reunión de kick-off" in result.output
    assert "Cierre de contrato" in result.output
    assert "4 entrada(s)" in result.output


def test_historial_persona_sin_datos(keel_tmp):
    guardar_persona(Persona(nombre="Ana"))
    result = runner.invoke(app, ["historial", "--persona", "Ana"])
    assert result.exit_code == 0
    assert "No hay historial" in result.output


def test_historial_persona_inexistente(keel_tmp):
    # cargar_persona devuelve Persona vacía si no existe
    result = runner.invoke(app, ["historial", "--persona", "Nadie"])
    assert result.exit_code == 0
    assert "No hay historial" in result.output


# ── Filtros ────────────────────────────────────────────────────────────────────

def test_historial_filtro_desde(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos", "--desde", "2026-04-01"])
    assert result.exit_code == 0
    assert "Cierre de contrato" in result.output
    assert "Llamada de seguimiento" in result.output
    assert "Reunión de kick-off" not in result.output


def test_historial_filtro_hasta(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos", "--hasta", "2026-03-31"])
    assert result.exit_code == 0
    assert "Reunión de kick-off" in result.output
    assert "Revisión de avances" in result.output
    assert "Cierre de contrato" not in result.output


def test_historial_filtro_rango(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos",
                                  "--desde", "2026-03-01", "--hasta", "2026-05-31"])
    assert result.exit_code == 0
    assert "Revisión de avances" in result.output
    assert "Cierre de contrato" in result.output
    assert "Reunión de kick-off" not in result.output
    assert "Llamada de seguimiento" not in result.output


def test_historial_top(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos", "--top", "2"])
    assert result.exit_code == 0
    # Los 2 más recientes
    assert "Cierre de contrato" in result.output
    assert "Llamada de seguimiento" in result.output
    assert "Reunión de kick-off" not in result.output


def test_historial_rango_sin_resultados(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos",
                                  "--desde", "2025-01-01", "--hasta", "2025-12-31"])
    assert result.exit_code == 0
    assert "Sin conversaciones" in result.output


# ── JSON ───────────────────────────────────────────────────────────────────────

def test_historial_json(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 4
    assert data[0]["fecha"] == "2026-01-10"
    assert data[-1]["fecha"] == "2026-06-01"


def test_historial_json_con_top(keel_tmp, persona_con_historial):
    result = runner.invoke(app, ["historial", "--persona", "Carlos", "--json", "--top", "2"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["fecha"] == "2026-05-20"


# ── Orden cronológico ──────────────────────────────────────────────────────────

def test_historial_ordenado_cronologicamente(keel_tmp):
    """El historial se muestra de más antiguo a más reciente."""
    p = Persona(nombre="María", historial_conversaciones=[
        ConversacionResumen(fecha="2026-06-01", resumen="Última"),
        ConversacionResumen(fecha="2026-01-01", resumen="Primera"),
        ConversacionResumen(fecha="2026-03-15", resumen="Intermedia"),
    ])
    guardar_persona(p)
    result = runner.invoke(app, ["historial", "--persona", "María", "--json"])
    data = json.loads(result.output)
    fechas = [d["fecha"] for d in data]
    assert fechas == sorted(fechas)
