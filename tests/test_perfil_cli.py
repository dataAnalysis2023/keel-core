"""Tests de keel perfil — show, editar, actualizar."""

import json
import subprocess
import pytest
import click
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_perfil

runner = CliRunner()
_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


# ── show ───────────────────────────────────────────────────────────────────────

def test_perfil_show(keel_tmp):
    guardar_perfil(PerfilUsuario(nombre="Juan Diego", valores=["claridad", "compromiso"]))
    result = runner.invoke(app, ["perfil", "show"])
    assert result.exit_code == 0
    assert "Juan Diego" in result.output
    assert "claridad" in result.output


def test_perfil_show_sin_perfil(keel_tmp):
    result = runner.invoke(app, ["perfil", "show"])
    assert result.exit_code != 0


# ── editar ─────────────────────────────────────────────────────────────────────

def test_perfil_editar_sin_perfil(keel_tmp):
    result = runner.invoke(app, ["perfil", "editar"])
    assert result.exit_code != 0
    assert "init" in result.output.lower() or "no encontrado" in result.output.lower()


def test_perfil_editar_llama_editor(keel_tmp, monkeypatch):
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    llamadas = []
    monkeypatch.setenv("EDITOR", "cat")  # cat no modifica nada
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: llamadas.append(cmd))
    result = runner.invoke(app, ["perfil", "editar"])
    assert result.exit_code == 0
    assert any("cat" in str(c) for c in llamadas)
    assert "✓" in result.output


def test_perfil_editar_detecta_json_invalido(keel_tmp, monkeypatch):
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    ruta = keel_tmp / "perfil.json"

    def _corromper(cmd, **kw):
        ruta.write_text("esto no es json {{{")

    monkeypatch.setattr(subprocess, "run", _corromper)
    result = runner.invoke(app, ["perfil", "editar"])
    assert result.exit_code == 0
    assert "válido" in result.output.lower() or "error" in result.output.lower()
    # El archivo queda corrupto pero el comando no falla en exit_code
    assert "revísalo" in result.output.lower() or "válid" in result.output.lower()
