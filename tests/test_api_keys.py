"""Tests de keel.security.api_keys — gestión de API keys de proveedores."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from keel.security.api_keys import (
    guardar_api_key,
    obtener_api_key,
    eliminar_api_key,
    proveedores_soportados,
    _validar_proveedor,
)


# ── proveedores_soportados ────────────────────────────────────────────────────

def test_proveedores_incluye_anthropic():
    assert "anthropic" in proveedores_soportados()

def test_proveedores_incluye_openai():
    assert "openai" in proveedores_soportados()


# ── _validar_proveedor ────────────────────────────────────────────────────────

def test_validar_proveedor_valido():
    _validar_proveedor("anthropic")  # no lanza

def test_validar_proveedor_invalido():
    with pytest.raises(ValueError, match="no soportado"):
        _validar_proveedor("gemini")


# ── guardar y obtener via archivo fallback ────────────────────────────────────

def test_guardar_obtener_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("keel.security.api_keys._archivo_fallback",
                        lambda p: tmp_path / f".api-key-{p}")
    with patch.dict("sys.modules", {"keyring": None}):
        guardar_api_key("anthropic", "sk-ant-test-key")
        resultado = obtener_api_key("anthropic")

    assert resultado == "sk-ant-test-key"
    assert (tmp_path / ".api-key-anthropic").stat().st_mode & 0o777 == 0o600


def test_obtener_ninguna(tmp_path, monkeypatch):
    monkeypatch.setattr("keel.security.api_keys._archivo_fallback",
                        lambda p: tmp_path / f".api-key-{p}")
    with patch.dict("sys.modules", {"keyring": None}):
        resultado = obtener_api_key("openai")
    assert resultado is None


def test_eliminar_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("keel.security.api_keys._archivo_fallback",
                        lambda p: tmp_path / f".api-key-{p}")
    ruta = tmp_path / ".api-key-anthropic"
    ruta.write_text("sk-ant-borrar")

    with patch.dict("sys.modules", {"keyring": None}):
        eliminar_api_key("anthropic")

    assert not ruta.exists()


def test_eliminar_inexistente_no_falla(tmp_path, monkeypatch):
    monkeypatch.setattr("keel.security.api_keys._archivo_fallback",
                        lambda p: tmp_path / f".api-key-{p}")
    with patch.dict("sys.modules", {"keyring": None}):
        eliminar_api_key("openai")  # no debe lanzar


# ── guardar y obtener via keyring ─────────────────────────────────────────────

def test_guardar_obtener_keyring(monkeypatch):
    store: dict[str, str] = {}
    mock_keyring = MagicMock()
    mock_keyring.set_password.side_effect = lambda svc, acc, val: store.__setitem__(acc, val)
    mock_keyring.get_password.side_effect = lambda svc, acc: store.get(acc)

    with patch.dict("sys.modules", {"keyring": mock_keyring}):
        guardar_api_key("anthropic", "sk-ant-keyring")
        resultado = obtener_api_key("anthropic")

    assert resultado == "sk-ant-keyring"
