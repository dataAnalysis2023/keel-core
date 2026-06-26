"""Tests del servidor MCP — verifica herramientas y recursos sin Ollama."""

import json
import pytest
import asyncio
import keel.storage.vectorial as mod_vectorial


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr("keel.storage.local._KEEL_DIR", keel)
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: keel / "vectorial")

    perfil = {
        "nombre": "Juan",
        "voz": {"tono": "directo", "registro": "informal", "vocabulario_frecuente": [], "frases_caracteristicas": []},
        "valores": ["claridad"],
        "contexto_vital": {},
        "historial_coherencia": [],
    }
    (keel / "perfil.json").write_text(json.dumps(perfil))
    return keel


async def _call(tool: str, args: dict):
    from keel.mcp.server import mcp
    content, _ = await mcp.call_tool(tool, args)
    return content[0].text


async def _resource(uri: str) -> str:
    from keel.mcp.server import mcp
    result = await mcp.read_resource(uri)
    return result[0].content if result else ""


def test_list_tools():
    from keel.mcp.server import mcp

    async def _run():
        tools = await mcp.list_tools()
        return [t.name for t in tools]

    nombres = asyncio.run(_run())
    assert "keel_get_context" in nombres
    assert "keel_respond" in nombres
    assert "keel_remember" in nombres
    assert "keel_list_personas" in nombres
    assert "keel_get_persona" in nombres


def test_list_personas_vacio(keel_tmp):
    texto = asyncio.run(_call("keel_list_personas", {}))
    assert "No hay" in texto


def test_get_context(keel_tmp):
    texto = asyncio.run(_call("keel_get_context", {
        "mensaje": "Hola, ¿cómo estás?",
        "remitente": "Ana",
    }))
    assert "Juan" in texto
    assert "Ana" in texto
    assert "claridad" in texto


def test_remember_con_persona(keel_tmp):
    texto = asyncio.run(_call("keel_remember", {
        "nota": "Hablamos del roadmap del proyecto",
        "persona": "Pedro",
        "temas": "roadmap,proyecto",
    }))
    assert "✓" in texto

    persona_json = asyncio.run(_call("keel_get_persona", {"nombre": "Pedro"}))
    persona = json.loads(persona_json)
    assert len(persona["historial_conversaciones"]) == 1


def test_remember_promesa(keel_tmp):
    texto = asyncio.run(_call("keel_remember", {
        "nota": "Prometí enviar el informe el viernes",
        "persona": "María",
    }))
    assert "promesa" in texto.lower() or "✓" in texto

    persona_json = asyncio.run(_call("keel_get_persona", {"nombre": "María"}))
    persona = json.loads(persona_json)
    assert len(persona["promesas_pendientes"]) == 1


def test_resource_perfil(keel_tmp):
    texto = asyncio.run(_resource("keel://perfil"))
    data = json.loads(texto)
    assert data["nombre"] == "Juan"


def test_resource_personas(keel_tmp):
    asyncio.run(_call("keel_remember", {"nota": "Nota", "persona": "Luis"}))
    texto = asyncio.run(_resource("keel://personas"))
    personas = json.loads(texto)
    assert any(p["nombre"] == "Luis" for p in personas)
