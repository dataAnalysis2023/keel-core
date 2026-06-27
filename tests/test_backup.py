"""Tests de keel backup y keel restaurar."""

import zipfile
import json
import pytest
from pathlib import Path
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil

runner = CliRunner()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


@pytest.fixture
def keel_con_datos(keel_tmp):
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    guardar_persona(Persona(nombre="Carlos", historial_conversaciones=[
        ConversacionResumen(fecha="2026-06-01", resumen="Reunión importante", temas=["producto"]),
    ]))
    return keel_tmp


# ── backup ────────────────────────────────────────────────────────────────────

def test_backup_crea_zip(keel_con_datos, tmp_path):
    destino = tmp_path / "backup.zip"
    result = runner.invoke(app, ["backup", "--output", str(destino)])
    assert result.exit_code == 0
    assert destino.exists()
    assert zipfile.is_zipfile(destino)


def test_backup_contiene_archivos(keel_con_datos, tmp_path):
    destino = tmp_path / "backup.zip"
    runner.invoke(app, ["backup", "--output", str(destino)])
    with zipfile.ZipFile(destino) as zf:
        nombres = zf.namelist()
    assert any("perfil.json" in n for n in nombres)
    assert any("carlos.json" in n for n in nombres)


def test_backup_output_en_mensaje(keel_con_datos, tmp_path):
    destino = tmp_path / "test.zip"
    result = runner.invoke(app, ["backup", "--output", str(destino)])
    assert result.exit_code == 0
    assert "✓" in result.output
    assert "test.zip" in result.output


def test_backup_sin_datos(keel_tmp, tmp_path):
    destino = tmp_path / "vacio.zip"
    result = runner.invoke(app, ["backup", "--output", str(destino)])
    assert result.exit_code == 0
    assert "No hay datos" in result.output
    assert not destino.exists()


def test_backup_contiene_conteo(keel_con_datos, tmp_path):
    destino = tmp_path / "backup.zip"
    result = runner.invoke(app, ["backup", "--output", str(destino)])
    assert result.exit_code == 0
    # Debe mencionar número de archivos y KB
    assert "archivo(s)" in result.output
    assert "KB" in result.output


# ── restaurar ─────────────────────────────────────────────────────────────────

def test_restaurar_archivo_inexistente(keel_tmp):
    result = runner.invoke(app, ["restaurar", "/ruta/no/existe.zip"])
    assert result.exit_code != 0
    assert "no encontrado" in result.output.lower()


def test_restaurar_archivo_invalido(keel_tmp, tmp_path):
    no_zip = tmp_path / "fake.zip"
    no_zip.write_text("esto no es un zip")
    result = runner.invoke(app, ["restaurar", str(no_zip)])
    assert result.exit_code != 0
    assert "ZIP válido" in result.output or "válido" in result.output


def test_restaurar_cancela(keel_con_datos, tmp_path):
    destino = tmp_path / "backup.zip"
    runner.invoke(app, ["backup", "--output", str(destino)])

    result = runner.invoke(app, ["restaurar", str(destino)], input="n\n")
    assert result.exit_code == 0
    assert "Cancelado" in result.output


def test_restaurar_forzar_recupera_datos(keel_tmp, tmp_path):
    """Flujo completo: guardar datos, backup, borrar, restaurar."""
    guardar_perfil(PerfilUsuario(nombre="Juan Recuperado"))
    guardar_persona(Persona(nombre="Ana"))

    destino = tmp_path / "backup.zip"
    runner.invoke(app, ["backup", "--output", str(destino)])

    # Simular pérdida — borrar perfil
    (keel_tmp / "perfil.json").unlink()
    assert not (keel_tmp / "perfil.json").exists()

    result = runner.invoke(app, ["restaurar", str(destino), "--forzar"])
    assert result.exit_code == 0
    assert "✓" in result.output

    # El perfil debe estar de vuelta
    assert (keel_tmp / "perfil.json").exists()
    perfil_texto = (keel_tmp / "perfil.json").read_text()
    assert "Juan Recuperado" in perfil_texto


def test_restaurar_preserva_personas(keel_tmp, tmp_path):
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    guardar_persona(Persona(nombre="Pedro", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Primera conversación", temas=[])
    ]))

    destino = tmp_path / "backup.zip"
    runner.invoke(app, ["backup", "--output", str(destino)])

    # Borrar persona
    (keel_tmp / "personas" / "pedro.json").unlink()

    runner.invoke(app, ["restaurar", str(destino), "--forzar"])

    assert (keel_tmp / "personas" / "pedro.json").exists()
    contenido = (keel_tmp / "personas" / "pedro.json").read_text()
    assert "Primera conversación" in contenido
