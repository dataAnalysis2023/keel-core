"""Tests Hito 5: agenda, contexto, MCP prompts."""

import json
import asyncio
import pytest
import keel.storage.vectorial as mod_vectorial
from fastapi.testclient import TestClient


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


def _persona_json(nombre, rol="", promesas=None):
    return json.dumps({
        "nombre": nombre, "rol": rol, "como_nos_conocemos": "", "tono_relacional": "neutro",
        "sensibilidades": [], "historial_conversaciones": [],
        "promesas_pendientes": promesas or [],
        "ultima_interaccion": None, "estado_actual": "",
    })


# ─── agenda ──────────────────────────────────────────────────────────────────

def test_agenda_vacia(keel_tmp):
    from keel.storage.local import keel_dir
    # Sin personas, sin promesas
    from keel.models.persona import Persona
    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json"))
    pendientes = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        pendientes.extend(p.promesas_pendientes)
    assert pendientes == []


def test_agenda_con_promesas(keel_tmp):
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona

    personas_dir = keel_dir() / "personas"
    (personas_dir / "carlos.json").write_text(_persona_json("Carlos", promesas=[
        {"descripcion": "Enviar informe", "fecha_compromiso": "2026-06-30"},
        {"descripcion": "Llamar el lunes", "fecha_compromiso": None},
    ]))
    (personas_dir / "ana.json").write_text(_persona_json("Ana", promesas=[
        {"descripcion": "Revisar propuesta", "fecha_compromiso": "2026-07-01"},
    ]))

    total = 0
    for archivo in sorted(personas_dir.glob("*.json")):
        p = Persona.model_validate_json(archivo.read_text())
        total += len(p.promesas_pendientes)
    assert total == 3


def test_agenda_detecta_vencidas(keel_tmp):
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from datetime import date

    personas_dir = keel_dir() / "personas"
    (personas_dir / "luis.json").write_text(_persona_json("Luis", promesas=[
        {"descripcion": "Tarea vencida", "fecha_compromiso": "2020-01-01"},
    ]))

    p = Persona.model_validate_json((personas_dir / "luis.json").read_text())
    hoy = date.today().isoformat()
    vencidas = [pr for pr in p.promesas_pendientes if pr.fecha_compromiso and pr.fecha_compromiso < hoy]
    assert len(vencidas) == 1


# ─── contexto ────────────────────────────────────────────────────────────────

def test_contexto_incluye_perfil_y_persona(keel_tmp):
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import construir_prompt

    perfil = cargar_perfil()
    persona = cargar_persona("María")
    prompt = construir_prompt(perfil, persona, "hola", "neutro")
    assert "Juan" in prompt
    assert "María" in prompt


def test_contexto_sin_mensaje_funciona(keel_tmp):
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import construir_prompt

    perfil = cargar_perfil()
    persona = cargar_persona("Pedro")
    prompt = construir_prompt(perfil, persona, "contexto general", "—")
    assert "Pedro" in prompt


# ─── MCP Prompts ─────────────────────────────────────────────────────────────

async def _prompt(nombre: str, args: dict) -> str:
    from keel.mcp.server import mcp
    result = await mcp.get_prompt(nombre, args)
    return result.messages[0].content.text


def test_mcp_list_prompts():
    from keel.mcp.server import mcp

    async def _run():
        return await mcp.list_prompts()

    prompts = asyncio.run(_run())
    nombres = [p.name for p in prompts]
    assert "keel_responder" in nombres
    assert "keel_agenda_prompt" in nombres


def test_mcp_prompt_responder(keel_tmp):
    texto = asyncio.run(_prompt("keel_responder", {
        "mensaje": "¿Puedes revisar el contrato?",
        "remitente": "Carlos",
    }))
    assert "Juan" in texto
    assert "Carlos" in texto


def test_mcp_prompt_agenda_vacia(keel_tmp):
    texto = asyncio.run(_prompt("keel_agenda_prompt", {}))
    assert "No hay" in texto


def test_mcp_prompt_agenda_con_promesas(keel_tmp):
    from keel.storage.local import keel_dir

    (keel_tmp / "personas" / "pedro.json").write_text(_persona_json("Pedro", promesas=[
        {"descripcion": "Llamar esta semana", "fecha_compromiso": "2026-06-28"},
    ]))

    texto = asyncio.run(_prompt("keel_agenda_prompt", {}))
    assert "Pedro" in texto
    assert "Llamar esta semana" in texto
