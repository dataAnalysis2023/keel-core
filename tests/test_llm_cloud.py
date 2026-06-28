"""Tests de proveedores cloud y factory LLM."""

import pytest
from unittest.mock import MagicMock, patch

from keel.models.config import ConfigKeel
from keel.llm.anthropic import AnthropicLLM
from keel.llm.openai_llm import OpenAILLM
from keel.llm.factory import crear_llm
from keel.llm.ollama import OllamaLLM


# ── ConfigKeel nuevos campos ──────────────────────────────────────────────────

def test_config_proveedor_default():
    cfg = ConfigKeel()
    assert cfg.proveedor == "ollama"

def test_config_modelo_cloud_default():
    cfg = ConfigKeel()
    assert cfg.modelo_cloud == ""

def test_config_proveedor_serializa():
    cfg = ConfigKeel(proveedor="anthropic", modelo_cloud="claude-haiku-4-5-20251001")
    data = cfg.model_dump()
    assert data["proveedor"] == "anthropic"
    assert data["modelo_cloud"] == "claude-haiku-4-5-20251001"

def test_config_retrocompatible():
    # JSON antiguo sin proveedor ni modelo_cloud → defaults
    cfg = ConfigKeel.model_validate({"dias_promesa": 5})
    assert cfg.proveedor == "ollama"
    assert cfg.modelo_cloud == ""
    assert cfg.dias_promesa == 5


# ── AnthropicLLM ──────────────────────────────────────────────────────────────

def test_anthropic_disponible_sin_sdk():
    llm = AnthropicLLM(api_key="sk-ant-test")
    with patch.dict("sys.modules", {"anthropic": None}):
        assert not llm.disponible()

def test_anthropic_disponible_sin_key():
    llm = AnthropicLLM(api_key="")
    assert not llm.disponible()

def test_anthropic_disponible_con_key(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "anthropic", MagicMock())
    llm = AnthropicLLM(api_key="sk-ant-test")
    assert llm.disponible()

def test_anthropic_generar_sin_sdk():
    llm = AnthropicLLM(api_key="sk-ant-test")
    with patch.dict("sys.modules", {"anthropic": None}):
        with pytest.raises(RuntimeError, match="SDK de Anthropic"):
            llm.generar("Hola")

def test_anthropic_generar_llama_api(monkeypatch):
    mock_anthropic = MagicMock()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="Respuesta de prueba")]
    mock_client.messages.create.return_value = mock_msg

    monkeypatch.setitem(__import__("sys").modules, "anthropic", mock_anthropic)
    llm = AnthropicLLM(api_key="sk-ant-test", modelo="claude-haiku-4-5-20251001")
    resultado = llm.generar("Pregunta de prueba")

    assert resultado == "Respuesta de prueba"
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

def test_anthropic_modelo_override(monkeypatch):
    mock_anthropic = MagicMock()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="ok")]
    mock_client.messages.create.return_value = mock_msg

    monkeypatch.setitem(__import__("sys").modules, "anthropic", mock_anthropic)
    llm = AnthropicLLM(api_key="sk-ant-test", modelo="claude-haiku-4-5-20251001")
    llm.generar("hola", modelo="claude-sonnet-4-6")

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"


# ── OpenAILLM ─────────────────────────────────────────────────────────────────

def test_openai_disponible_sin_sdk():
    llm = OpenAILLM(api_key="sk-test")
    with patch.dict("sys.modules", {"openai": None}):
        assert not llm.disponible()

def test_openai_disponible_sin_key():
    llm = OpenAILLM(api_key="")
    assert not llm.disponible()

def test_openai_generar_sin_sdk():
    llm = OpenAILLM(api_key="sk-test")
    with patch.dict("sys.modules", {"openai": None}):
        with pytest.raises(RuntimeError, match="SDK de OpenAI"):
            llm.generar("Hola")

def test_openai_generar_llama_api(monkeypatch):
    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content="Respuesta OpenAI"))]
    mock_client.chat.completions.create.return_value = mock_resp

    monkeypatch.setitem(__import__("sys").modules, "openai", mock_openai)
    llm = OpenAILLM(api_key="sk-test", modelo="gpt-4o-mini")
    resultado = llm.generar("Pregunta")

    assert resultado == "Respuesta OpenAI"
    mock_client.chat.completions.create.assert_called_once()


# ── factory crear_llm ─────────────────────────────────────────────────────────

def test_factory_ollama_por_defecto():
    cfg = ConfigKeel()
    llm = crear_llm(cfg)
    assert isinstance(llm, OllamaLLM)

def test_factory_ollama_modelo_override():
    cfg = ConfigKeel(modelo_ollama="mistral")
    llm = crear_llm(cfg, modelo_override="llama3")
    assert isinstance(llm, OllamaLLM)
    assert llm.modelo_default == "llama3"

def test_factory_ollama_modelo_desde_config():
    cfg = ConfigKeel(modelo_ollama="phi3")
    llm = crear_llm(cfg)
    assert isinstance(llm, OllamaLLM)
    assert llm.modelo_default == "phi3"

def test_factory_anthropic_sin_key():
    cfg = ConfigKeel(proveedor="anthropic")
    with patch("keel.security.api_keys.obtener_api_key", return_value=None):
        with pytest.raises(RuntimeError, match="API key de Anthropic"):
            crear_llm(cfg)

def test_factory_anthropic_con_key():
    cfg = ConfigKeel(proveedor="anthropic")
    with patch("keel.security.api_keys.obtener_api_key", return_value="sk-ant-test"):
        llm = crear_llm(cfg)
    assert isinstance(llm, AnthropicLLM)

def test_factory_openai_sin_key():
    cfg = ConfigKeel(proveedor="openai")
    with patch("keel.security.api_keys.obtener_api_key", return_value=None):
        with pytest.raises(RuntimeError, match="API key de OpenAI"):
            crear_llm(cfg)

def test_factory_openai_con_key():
    cfg = ConfigKeel(proveedor="openai")
    with patch("keel.security.api_keys.obtener_api_key", return_value="sk-test"):
        llm = crear_llm(cfg)
    assert isinstance(llm, OpenAILLM)

def test_factory_proveedor_desconocido():
    cfg = ConfigKeel(proveedor="gemini")  # type: ignore
    with pytest.raises(ValueError, match="desconocido"):
        crear_llm(cfg)

def test_factory_cloud_modelo_override():
    cfg = ConfigKeel(proveedor="anthropic", modelo_cloud="claude-haiku-4-5-20251001")
    with patch("keel.security.api_keys.obtener_api_key", return_value="sk-ant-test"):
        llm = crear_llm(cfg, modelo_override="claude-sonnet-4-6")
    assert isinstance(llm, AnthropicLLM)
    assert llm.modelo_default == "claude-sonnet-4-6"
