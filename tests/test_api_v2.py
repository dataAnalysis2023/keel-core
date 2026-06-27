"""Tests de los nuevos endpoints REST — buscar, reflexion, agenda, aprendizaje."""

import json
import pytest
import keel.storage.local as mod_local
import keel.storage.vectorial as mod_vectorial

from fastapi.testclient import TestClient
from keel.api.app import create_app
from keel.models.persona import Persona, PromesaPendiente, ConversacionResumen
from keel.storage.local import guardar_persona, guardar_perfil
from keel.models.perfil import PerfilUsuario


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: keel / "vectorial")
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    return keel


@pytest.fixture
def client(keel_tmp):
    return TestClient(create_app())


# ── /buscar ───────────────────────────────────────────────────────────────────

def test_buscar_sin_historial(client):
    r = client.post("/buscar", json={"texto": "producto"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_buscar_con_historial(client, keel_tmp):
    p = Persona(nombre="Carlos", historial_conversaciones=[
        ConversacionResumen(fecha="2026-06-01", resumen="Lanzamiento del producto", temas=["producto"])
    ])
    guardar_persona(p)

    r = client.post("/buscar", json={"texto": "lanzamiento"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["resultados"][0]["persona"] == "Carlos"


def test_buscar_filtro_persona(client, keel_tmp):
    for nombre, resumen in [("Carlos", "Reunión de producto"), ("Ana", "Tema legal")]:
        guardar_persona(Persona(nombre=nombre, historial_conversaciones=[
            ConversacionResumen(fecha="2026-06-01", resumen=resumen, temas=[])
        ]))

    r = client.post("/buscar", json={"texto": "reunión", "persona": "Carlos"})
    assert r.status_code == 200
    for resultado in r.json()["resultados"]:
        assert resultado["persona"] == "Carlos"


# ── /reflexion ────────────────────────────────────────────────────────────────

def test_reflexion_sin_personas(client):
    r = client.get("/reflexion")
    assert r.status_code == 200
    data = r.json()
    assert "promesas_proximas" in data
    assert data["promesas_proximas"] == []


def test_reflexion_con_promesa_urgente(client, keel_tmp):
    from datetime import date, timedelta
    vence = (date.today() + timedelta(days=3)).isoformat()
    p = Persona(nombre="Ana", promesas_pendientes=[
        PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso=vence)
    ])
    guardar_persona(p)

    r = client.get("/reflexion?dias_promesa=7")
    assert r.status_code == 200
    assert len(r.json()["promesas_proximas"]) == 1


def test_reflexion_formato_markdown(client, keel_tmp):
    r = client.get("/reflexion?formato=markdown")
    assert r.status_code == 200
    assert "markdown" in r.json()
    assert "Reflexión" in r.json()["markdown"]


# ── /agenda ───────────────────────────────────────────────────────────────────

def test_agenda_vacia(client):
    r = client.get("/agenda")
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_agenda_lista_promesas(client, keel_tmp):
    guardar_persona(Persona(nombre="Carlos", promesas_pendientes=[
        PromesaPendiente(descripcion="Llamar cliente", fecha_compromiso="2026-07-10")
    ]))
    r = client.get("/agenda")
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["pendientes"][0]["persona"] == "Carlos"


def test_agenda_completar(client, keel_tmp):
    guardar_persona(Persona(nombre="María", promesas_pendientes=[
        PromesaPendiente(descripcion="Enviar informe")
    ]))
    r = client.post("/agenda/María/completar", json={"indice": 0})
    assert r.status_code == 200
    assert r.json()["pendientes"] == 0


def test_agenda_completar_indice_invalido(client, keel_tmp):
    guardar_persona(Persona(nombre="Luis"))
    r = client.post("/agenda/Luis/completar", json={"indice": 99})
    assert r.status_code == 404


def test_agenda_posponer(client, keel_tmp):
    guardar_persona(Persona(nombre="Pedro", promesas_pendientes=[
        PromesaPendiente(descripcion="Reunión", fecha_compromiso="2026-06-30")
    ]))
    r = client.patch("/agenda/Pedro/posponer", json={"indice": 0, "fecha": "2026-07-15"})
    assert r.status_code == 200
    assert r.json()["nueva"] == "2026-07-15"


def test_agenda_posponer_fecha_invalida(client, keel_tmp):
    guardar_persona(Persona(nombre="Pedro", promesas_pendientes=[
        PromesaPendiente(descripcion="Algo")
    ]))
    r = client.patch("/agenda/Pedro/posponer", json={"indice": 0, "fecha": "no-fecha"})
    assert r.status_code == 422


# ── /aprendizaje ──────────────────────────────────────────────────────────────

def test_aprendizaje_sin_historial(client, keel_tmp):
    # Sin Ollama y sin historial → respuesta informativa, no error 500
    r = client.post("/aprendizaje/analizar")
    # Puede ser 200 (sin historial), 503 (Ollama no disponible) — ambos son válidos
    assert r.status_code in (200, 503)


def test_aprendizaje_sin_perfil(client, keel_tmp):
    (keel_tmp / "perfil.json").unlink()
    r = client.post("/aprendizaje/analizar")
    assert r.status_code == 404
