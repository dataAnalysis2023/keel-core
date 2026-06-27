"""Tests de keel config — modelo, storage y CLI."""

import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.config import ConfigKeel
from keel.storage.local import cargar_config, guardar_config
import click.exceptions


_EXIT = (SystemExit, click.exceptions.Exit)
runner = CliRunner()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


# ── Modelo ────────────────────────────────────────────────────────────────────

def test_config_defaults():
    cfg = ConfigKeel()
    assert cfg.vault_obsidian == ""
    assert cfg.modelo_ollama == ""
    assert cfg.dias_promesa == 7
    assert cfg.dias_silencio == 14
    assert cfg.min_conversaciones_aprendizaje == 2
    assert cfg.clipboard_no_guardar is False


def test_config_serializa_y_deserializa():
    cfg = ConfigKeel(vault_obsidian="/ruta/vault", dias_promesa=5)
    json_str = cfg.model_dump_json()
    cfg2 = ConfigKeel.model_validate_json(json_str)
    assert cfg2.vault_obsidian == "/ruta/vault"
    assert cfg2.dias_promesa == 5


# ── Storage ───────────────────────────────────────────────────────────────────

def test_cargar_config_sin_archivo(keel_tmp):
    cfg = cargar_config()
    assert cfg.dias_promesa == 7  # default


def test_guardar_y_cargar_config(keel_tmp):
    cfg = ConfigKeel(dias_promesa=10, dias_silencio=30)
    guardar_config(cfg)
    cfg2 = cargar_config()
    assert cfg2.dias_promesa == 10
    assert cfg2.dias_silencio == 30


def test_config_archivo_creado(keel_tmp):
    guardar_config(ConfigKeel(vault_obsidian="~/Notas"))
    assert (keel_tmp / "config.json").exists()


# ── CLI: keel config ver ──────────────────────────────────────────────────────

def test_config_ver_defaults(keel_tmp):
    result = runner.invoke(app, ["config", "ver"])
    assert result.exit_code == 0
    assert "dias_promesa" in result.output
    assert "vault_obsidian" in result.output


def test_config_ver_con_valores(keel_tmp):
    guardar_config(ConfigKeel(dias_promesa=5, vault_obsidian="~/MiVault"))
    result = runner.invoke(app, ["config", "ver"])
    assert result.exit_code == 0
    assert "5" in result.output
    assert "~/MiVault" in result.output


# ── CLI: keel config set ──────────────────────────────────────────────────────

def test_config_set_int(keel_tmp):
    result = runner.invoke(app, ["config", "set", "dias_promesa", "3"])
    assert result.exit_code == 0
    assert cargar_config().dias_promesa == 3


def test_config_set_str(keel_tmp):
    result = runner.invoke(app, ["config", "set", "vault_obsidian", "~/Notas"])
    assert result.exit_code == 0
    assert cargar_config().vault_obsidian == "~/Notas"


def test_config_set_bool_true(keel_tmp):
    result = runner.invoke(app, ["config", "set", "clipboard_no_guardar", "true"])
    assert result.exit_code == 0
    assert cargar_config().clipboard_no_guardar is True


def test_config_set_bool_false(keel_tmp):
    guardar_config(ConfigKeel(clipboard_no_guardar=True))
    result = runner.invoke(app, ["config", "set", "clipboard_no_guardar", "false"])
    assert result.exit_code == 0
    assert cargar_config().clipboard_no_guardar is False


def test_config_set_clave_desconocida(keel_tmp):
    result = runner.invoke(app, ["config", "set", "clave_inexistente", "valor"])
    assert result.exit_code != 0
    assert "desconocida" in result.output.lower() or "válidas" in result.output.lower()


def test_config_set_int_invalido(keel_tmp):
    result = runner.invoke(app, ["config", "set", "dias_promesa", "no-es-numero"])
    assert result.exit_code != 0


# ── CLI: keel config reset ────────────────────────────────────────────────────

def test_config_reset_cancela(keel_tmp):
    guardar_config(ConfigKeel(dias_promesa=99))
    result = runner.invoke(app, ["config", "reset"], input="n\n")
    assert result.exit_code == 0
    assert cargar_config().dias_promesa == 99  # no cambió


def test_config_reset_confirma(keel_tmp):
    guardar_config(ConfigKeel(dias_promesa=99))
    result = runner.invoke(app, ["config", "reset"], input="y\n")
    assert result.exit_code == 0
    assert cargar_config().dias_promesa == 7  # volvió a default


# ── Integración: config surte efecto en reflexionar ───────────────────────────

def test_reflexionar_usa_dias_de_config(keel_tmp, monkeypatch):
    """Si config.dias_promesa=3, reflexionar lo usa sin flag explícito."""
    from keel.models.persona import Persona
    from keel.storage.local import guardar_perfil, guardar_persona
    from keel.models.perfil import PerfilUsuario
    from datetime import date, timedelta

    guardar_perfil(PerfilUsuario(nombre="Juan"))
    vence = (date.today() + timedelta(days=2)).isoformat()
    guardar_persona(Persona(nombre="Ana", promesas_pendientes=[
        __import__('keel.models.persona', fromlist=['PromesaPendiente']).PromesaPendiente(
            descripcion="Algo", fecha_compromiso=vence
        )
    ]))

    guardar_config(ConfigKeel(dias_promesa=3))

    captured = {}

    def fake_digest(personas, hoy=None, dias_promesa=7, dias_sin_contacto=14):
        captured["dias_promesa"] = dias_promesa
        from keel.models.reflexion import DigestRelacional
        from datetime import date as _date
        return DigestRelacional(fecha=_date.today().isoformat())

    monkeypatch.setattr("keel.cli.main.construir_digest" if hasattr(__import__('keel.cli.main', fromlist=['construir_digest']), 'construir_digest') else "keel.engine.reflexion.construir_digest", fake_digest, raising=False)

    import keel.engine.reflexion as mod_ref
    original = mod_ref.construir_digest
    mod_ref.construir_digest = fake_digest

    result = runner.invoke(app, ["reflexionar", "--sin-llm"])

    mod_ref.construir_digest = original

    assert captured.get("dias_promesa") == 3
