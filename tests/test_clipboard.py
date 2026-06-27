"""Tests del canal clipboard."""

import subprocess
import sys
import pytest

from keel.io.clipboard import leer, escribir


# ── leer ──────────────────────────────────────────────────────────────────────

def test_leer_devuelve_texto(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="Hola mundo\n", stderr=""),
    )
    assert leer() == "Hola mundo\n"


def test_leer_clipboard_vacio_lanza_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="   ", stderr=""),
    )
    with pytest.raises(RuntimeError, match="vacío"):
        leer()


def test_leer_pbpaste_falla_lanza_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error"),
    )
    with pytest.raises(RuntimeError, match="pbpaste"):
        leer()


def test_leer_no_macos_lanza_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(RuntimeError, match="macOS"):
        leer()


# ── escribir ──────────────────────────────────────────────────────────────────

def test_escribir_llama_pbcopy(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    llamadas = []
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: (llamadas.append((cmd, kw)) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")),
    )
    escribir("Texto de prueba")
    assert llamadas[0][0] == ["pbcopy"]
    assert llamadas[0][1]["input"] == "Texto de prueba"


def test_escribir_pbcopy_falla_lanza_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, stdout="", stderr="error"),
    )
    with pytest.raises(RuntimeError, match="pbcopy"):
        escribir("algo")


def test_escribir_no_macos_lanza_error(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(RuntimeError, match="macOS"):
        escribir("algo")
