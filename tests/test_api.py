"""Tests de la API REST — usa TestClient de FastAPI, sin Ollama."""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

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


@pytest.fixture
def client(keel_tmp):
    from keel.api.app import create_app
    return TestClient(create_app())


def test_status(client):
    r = client.get("/status")
    assert r.status_code == 200
    data = r.json()
    assert "ollama" in data
    assert data["perfil"] is True
    assert data["personas"] == 0


def test_get_perfil(client):
    r = client.get("/perfil")
    assert r.status_code == 200
    assert r.json()["nombre"] == "Juan"


def test_get_perfil_no_existe(tmp_path, monkeypatch):
    vacio = tmp_path / ".keel_vacio"
    vacio.mkdir()
    monkeypatch.setattr("keel.storage.local._KEEL_DIR", vacio)
    from keel.api.app import create_app
    c = TestClient(create_app())
    r = c.get("/perfil")
    assert r.status_code == 404


def test_list_personas_vacio(client):
    r = client.get("/personas")
    assert r.status_code == 200
    assert r.json() == []


def test_create_y_get_persona(client):
    r = client.post("/personas/Carlos", json={"rol": "socio", "tono_relacional": "informal"})
    assert r.status_code == 200
    assert r.json()["rol"] == "socio"

    r2 = client.get("/personas/Carlos")
    assert r2.status_code == 200
    assert r2.json()["nombre"] == "Carlos"


def test_list_personas_con_datos(client):
    client.post("/personas/Ana", json={"rol": "diseñadora"})
    client.post("/personas/Luis", json={"rol": "dev"})
    r = client.get("/personas")
    assert r.status_code == 200
    nombres = [p["nombre"] for p in r.json()]
    assert "Ana" in nombres
    assert "Luis" in nombres


def test_remember_sin_persona(client):
    r = client.post("/remember", json={"nota": "Nota general sin persona", "temas": ["test"]})
    assert r.status_code == 200
    assert r.json()["guardado"] is False  # sin persona no se guarda en JSON


def test_remember_con_persona(client):
    client.post("/personas/Carlos", json={"rol": "socio"})
    r = client.post("/remember", json={"nota": "Hablamos del proyecto", "persona": "Carlos", "temas": ["proyecto"]})
    assert r.status_code == 200
    assert r.json()["guardado"] is True

    # Verifica que se guardó en el perfil de la persona
    persona = client.get("/personas/Carlos").json()
    assert len(persona["historial_conversaciones"]) == 1
