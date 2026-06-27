"""Tests de keel.cli.utils — picker de remitente."""

import json
import pytest
from pathlib import Path
from rich.console import Console

from keel.cli.utils import seleccionar_remitente
from keel.models.persona import Persona


@pytest.fixture
def personas_dir(tmp_path):
    d = tmp_path / "personas"
    d.mkdir()
    # Ordenadas alfabéticamente: Ana=1, Carlos=2, María=3, Marcos=4
    for nombre, rol in [("Carlos", "socio"), ("María", "cliente"), ("Ana", ""), ("Marcos", "aliado")]:
        p = Persona(nombre=nombre, rol=rol, ultima_interaccion="2026-06-20" if nombre != "Ana" else None)
        (d / f"{nombre.lower()}.json").write_text(p.model_dump_json())
    return tmp_path  # devuelve keel_dir (padre de personas/)


def _picker(tmp_path, entrada, monkeypatch):
    """Ejecuta seleccionar_remitente con entrada simulada."""
    import keel.cli.utils as mod
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **kw: entrada)
    return seleccionar_remitente(Console(quiet=True), tmp_path)


def test_seleccion_por_numero(personas_dir, monkeypatch):
    # Orden alfabético: Ana=1, Carlos=2, Marcos=3, María=4
    resultado = _picker(personas_dir, "1", monkeypatch)
    assert resultado == "Ana"


def test_seleccion_por_numero_dos(personas_dir, monkeypatch):
    resultado = _picker(personas_dir, "2", monkeypatch)
    assert resultado == "Carlos"


def test_seleccion_por_nombre_exacto(personas_dir, monkeypatch):
    resultado = _picker(personas_dir, "Ana", monkeypatch)
    assert resultado == "Ana"


def test_seleccion_por_prefijo(personas_dir, monkeypatch):
    resultado = _picker(personas_dir, "car", monkeypatch)
    assert resultado == "Carlos"


def test_numero_fuera_de_rango_lanza_exit(personas_dir, monkeypatch):
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **kw: "99")
    with pytest.raises(SystemExit):
        seleccionar_remitente(Console(quiet=True), personas_dir)


def test_prefijo_ambiguo_lanza_exit(personas_dir, monkeypatch):
    # "M" coincide con Marcos y María → ambiguo
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **kw: "M")
    with pytest.raises(SystemExit):
        seleccionar_remitente(Console(quiet=True), personas_dir)


def test_nombre_inexistente_lanza_exit(personas_dir, monkeypatch):
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **kw: "Pedro")
    with pytest.raises(SystemExit):
        seleccionar_remitente(Console(quiet=True), personas_dir)


def test_sin_personas_lanza_exit(tmp_path, monkeypatch):
    (tmp_path / "personas").mkdir()
    with pytest.raises(SystemExit):
        seleccionar_remitente(Console(quiet=True), tmp_path)
