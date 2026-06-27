"""Tests de keel status mejorado."""

import pytest
import keel.storage.local as mod_local
import keel.storage.vectorial as mod_vectorial
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.models.perfil import PerfilUsuario
from keel.models.config import ConfigKeel
from keel.storage.local import guardar_persona, guardar_perfil, guardar_config

runner = CliRunner(env={"COLUMNS": "200"})


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: keel / "vectorial")
    return keel


@pytest.fixture
def keel_poblado(keel_tmp):
    guardar_perfil(PerfilUsuario(nombre="Juan Diego"))
    guardar_persona(Persona(
        nombre="Carlos",
        ultima_interaccion="2026-06-15",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-06-15", resumen="Reunión", temas=[])
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Enviar informe")
        ],
    ))
    guardar_persona(Persona(nombre="Ana"))
    return keel_tmp


# ── Contenido esperado ────────────────────────────────────────────────────────

def test_status_muestra_version(keel_tmp):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Debe mencionar la versión (sea "dev" o un número)
    assert "keel-core" in result.output


def test_status_perfil_configurado(keel_poblado):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Juan Diego" in result.output


def test_status_perfil_no_encontrado(keel_tmp):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Sin perfil debe mencionar "init" o "Perfil" de alguna forma
    assert "init" in result.output or "Perfil" in result.output


def test_status_cuenta_personas(keel_poblado):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "2" in result.output  # 2 personas


def test_status_ultima_actividad(keel_poblado):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "2026-06-15" in result.output


def test_status_total_conversaciones(keel_poblado):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "1" in result.output  # 1 conversación


def test_status_promesas_pendientes(keel_poblado):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Promesas" in result.output


def test_status_muestra_config(keel_poblado):
    guardar_config(ConfigKeel(vault_obsidian="~/MiVault", dias_promesa=3))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "~/MiVault" in result.output
    assert "3" in result.output


def test_status_sin_cifrado(keel_tmp):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "inactivo" in result.output or "Cifrado" in result.output


def test_status_con_cifrado(keel_tmp):
    (keel_tmp / ".cifrado").touch()
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "AES-256-GCM" in result.output or "activo" in result.output


def test_status_muestra_storage(keel_tmp):
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "KB" in result.output or "MB" in result.output


def test_status_exit_code_ok(keel_tmp):
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
