"""Tests de keel.engine.reflexion."""

from datetime import date, timedelta

import pytest

from keel.engine.reflexion import (
    construir_digest,
    construir_sintesis,
    digest_a_markdown,
)
from keel.models.persona import Persona, PromesaPendiente, ConversacionResumen
from keel.models.reflexion import DigestRelacional


HOY = date(2026, 6, 26)


def _persona(nombre, ultima=None, promesas=None, conversaciones=None):
    return Persona(
        nombre=nombre,
        ultima_interaccion=ultima,
        promesas_pendientes=promesas or [],
        historial_conversaciones=conversaciones or [],
    )


# ── promesas próximas ─────────────────────────────────────────────────────────

def test_promesa_dentro_de_ventana():
    vence = (HOY + timedelta(days=3)).isoformat()
    p = _persona("Carlos", promesas=[PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso=vence)])
    digest = construir_digest([p], hoy=HOY, dias_promesa=7)
    assert len(digest.promesas_proximas) == 1
    assert digest.promesas_proximas[0].dias_restantes == 3


def test_promesa_fuera_de_ventana_no_aparece():
    vence = (HOY + timedelta(days=10)).isoformat()
    p = _persona("Ana", promesas=[PromesaPendiente(descripcion="Algo", fecha_compromiso=vence)])
    digest = construir_digest([p], hoy=HOY, dias_promesa=7)
    assert len(digest.promesas_proximas) == 0


def test_promesa_vencida_aparece():
    vence = (HOY - timedelta(days=2)).isoformat()
    p = _persona("Luis", promesas=[PromesaPendiente(descripcion="Vencida", fecha_compromiso=vence)])
    digest = construir_digest([p], hoy=HOY, dias_promesa=7)
    assert digest.promesas_proximas[0].dias_restantes == -2


def test_promesa_sin_fecha_se_omite():
    p = _persona("Marta", promesas=[PromesaPendiente(descripcion="Sin fecha")])
    digest = construir_digest([p], hoy=HOY)
    assert len(digest.promesas_proximas) == 0


# ── personas sin contacto ─────────────────────────────────────────────────────

def test_persona_sin_contacto_detectada():
    ultima = (HOY - timedelta(days=20)).isoformat()
    p = _persona("Pedro", ultima=ultima)
    digest = construir_digest([p], hoy=HOY, dias_sin_contacto=14)
    assert len(digest.personas_sin_contacto) == 1
    assert digest.personas_sin_contacto[0].dias_sin_contacto == 20


def test_persona_con_contacto_reciente_no_aparece():
    ultima = (HOY - timedelta(days=5)).isoformat()
    p = _persona("Julia", ultima=ultima)
    digest = construir_digest([p], hoy=HOY, dias_sin_contacto=14)
    assert len(digest.personas_sin_contacto) == 0


def test_persona_sin_ultima_interaccion_se_omite():
    p = _persona("Nuevo")
    digest = construir_digest([p], hoy=HOY)
    assert len(digest.personas_sin_contacto) == 0


# ── temas recurrentes ─────────────────────────────────────────────────────────

def test_temas_recurrentes_ordenados_por_frecuencia():
    convs = [
        ConversacionResumen(fecha="2026-06-01", resumen="x", temas=["producto", "legal"]),
        ConversacionResumen(fecha="2026-06-05", resumen="y", temas=["producto", "finanzas"]),
        ConversacionResumen(fecha="2026-06-10", resumen="z", temas=["producto"]),
    ]
    p = _persona("Ana", conversaciones=convs)
    digest = construir_digest([p], hoy=HOY)
    assert digest.temas_recurrentes[0] == "producto"


def test_tema_que_aparece_una_sola_vez_no_incluido():
    convs = [ConversacionResumen(fecha="2026-06-01", resumen="x", temas=["unico"])]
    p = _persona("Bob", conversaciones=convs)
    digest = construir_digest([p], hoy=HOY)
    assert "unico" not in digest.temas_recurrentes


# ── digest a markdown ─────────────────────────────────────────────────────────

def test_markdown_contiene_fecha():
    digest = DigestRelacional(fecha="2026-06-26")
    md = digest_a_markdown(digest)
    assert "2026-06-26" in md


def test_markdown_con_sintesis():
    digest = DigestRelacional(fecha="2026-06-26")
    md = digest_a_markdown(digest, sintesis="Esta semana sin urgencias.")
    assert "Esta semana sin urgencias." in md


def test_markdown_sin_datos_no_rompe():
    digest = DigestRelacional(fecha="2026-06-26")
    md = digest_a_markdown(digest)
    assert "# Reflexión" in md


# ── síntesis LLM ─────────────────────────────────────────────────────────────

def test_sintesis_digest_vacio():
    class _LLM:
        def generar(self, prompt, modelo=None): return "OK"

    digest = DigestRelacional(fecha="2026-06-26")
    resultado = construir_sintesis(digest, "Juan", _LLM())
    assert "Sin compromisos" in resultado


def test_sintesis_llama_llm_con_contexto():
    prompts = []

    class _LLM:
        def generar(self, prompt, modelo=None):
            prompts.append(prompt)
            return "síntesis generada"

    vence = (HOY + timedelta(days=2)).isoformat()
    p = _persona("Carlos", promesas=[PromesaPendiente(descripcion="Llamar", fecha_compromiso=vence)])
    digest = construir_digest([p], hoy=HOY)
    construir_sintesis(digest, "Juan", _LLM())

    assert "Carlos" in prompts[0]
    assert "Juan" in prompts[0]
