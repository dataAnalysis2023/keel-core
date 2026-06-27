"""Tests de keel alias — storage y CLI."""

import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.storage.local import (
    cargar_aliases, guardar_aliases, resolver_alias,
    cargar_persona, guardar_persona,
)
from keel.models.persona import Persona

runner = CliRunner(env={"COLUMNS": "200"})
_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


# ── cargar / guardar aliases ──────────────────────────────────────────────────

def test_cargar_aliases_vacio(keel_tmp):
    assert cargar_aliases() == {}


def test_guardar_y_cargar_alias(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos", "ceo": "Pedro"})
    resultado = cargar_aliases()
    assert resultado["jc"] == "Juan Carlos"
    assert resultado["ceo"] == "Pedro"


def test_alias_persiste_en_disco(keel_tmp):
    guardar_aliases({"ana": "Ana García"})
    assert (keel_tmp / "aliases.json").exists()


# ── resolver_alias ────────────────────────────────────────────────────────────

def test_resolver_alias_existente(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    assert resolver_alias("jc") == "Juan Carlos"


def test_resolver_alias_inexistente_devuelve_original(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    assert resolver_alias("pedro") == "pedro"


def test_resolver_alias_case_insensitive(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    assert resolver_alias("JC") == "Juan Carlos"
    assert resolver_alias("Jc") == "Juan Carlos"


def test_resolver_alias_sin_archivo(keel_tmp):
    assert resolver_alias("cualquier_cosa") == "cualquier_cosa"


# ── cargar_persona resuelve alias automáticamente ────────────────────────────

def test_cargar_persona_via_alias(keel_tmp):
    persona = Persona(nombre="Juan Carlos", rol="CEO")
    guardar_persona(persona)
    guardar_aliases({"jc": "Juan Carlos"})

    cargada = cargar_persona("jc")
    assert cargada.nombre == "Juan Carlos"
    assert cargada.rol == "CEO"


def test_cargar_persona_alias_inexistente_devuelve_vacia(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    # "jc" apunta a "Juan Carlos" pero el JSON no existe — devuelve Persona vacía con el nombre resuelto
    cargada = cargar_persona("jc")
    assert cargada.nombre == "Juan Carlos"
    assert not cargada.historial_conversaciones


def test_cargar_persona_sin_alias_ni_json(keel_tmp):
    cargada = cargar_persona("nadie")
    assert cargada.nombre == "nadie"


# ── CLI: keel alias add ───────────────────────────────────────────────────────

def test_cli_add_crea_alias(keel_tmp):
    result = runner.invoke(app, ["alias", "add", "jc", "Juan Carlos"])
    assert result.exit_code == 0
    assert "creado" in result.output.lower()
    assert cargar_aliases().get("jc") == "Juan Carlos"


def test_cli_add_actualiza_alias_existente(keel_tmp):
    guardar_aliases({"jc": "Juan C."})
    result = runner.invoke(app, ["alias", "add", "jc", "Juan Carlos"])
    assert result.exit_code == 0
    assert "actualizado" in result.output.lower()
    assert cargar_aliases()["jc"] == "Juan Carlos"


def test_cli_add_alias_guardado_en_minuscula(keel_tmp):
    result = runner.invoke(app, ["alias", "add", "CEO", "Pedro"])
    assert result.exit_code == 0
    aliases = cargar_aliases()
    assert "ceo" in aliases
    assert "CEO" not in aliases


def test_cli_add_advierte_si_persona_existe(keel_tmp):
    guardar_persona(Persona(nombre="carlos"))
    result = runner.invoke(app, ["alias", "add", "carlos", "Carlos Alberto"])
    assert result.exit_code == 0
    assert "ya existe" in result.output.lower() or "⚠" in result.output


# ── CLI: keel alias list ──────────────────────────────────────────────────────

def test_cli_list_sin_aliases(keel_tmp):
    result = runner.invoke(app, ["alias", "list"])
    assert result.exit_code == 0
    assert "no hay" in result.output.lower()


def test_cli_list_muestra_aliases(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos", "ceo": "Pedro"})
    result = runner.invoke(app, ["alias", "list"])
    assert result.exit_code == 0
    assert "jc" in result.output
    assert "Juan Carlos" in result.output
    assert "ceo" in result.output
    assert "Pedro" in result.output


def test_cli_list_muestra_total(keel_tmp):
    guardar_aliases({"a": "Ana", "b": "Beatriz"})
    result = runner.invoke(app, ["alias", "list"])
    assert result.exit_code == 0
    assert "2" in result.output


# ── CLI: keel alias borrar ────────────────────────────────────────────────────

def test_cli_borrar_existente(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    result = runner.invoke(app, ["alias", "borrar", "jc"])
    assert result.exit_code == 0
    assert "eliminado" in result.output.lower()
    assert "jc" not in cargar_aliases()


def test_cli_borrar_inexistente_falla(keel_tmp):
    result = runner.invoke(app, ["alias", "borrar", "fantasma"])
    assert result.exit_code != 0


def test_cli_borrar_case_insensitive(keel_tmp):
    guardar_aliases({"jc": "Juan Carlos"})
    result = runner.invoke(app, ["alias", "borrar", "JC"])
    assert result.exit_code == 0
    assert "jc" not in cargar_aliases()
