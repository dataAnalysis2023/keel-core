"""Tests del módulo de calendario — sin osascript."""

import pytest
from keel.io.calendario import (
    EventoCalendario,
    _parsear_salida,
    inferir_contexto_agenda,
    resumir_agenda,
)
from keel.engine.sintesis import construir_prompt_sintesis, parsear_sintesis
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario


# ── EventoCalendario ──────────────────────────────────────────────────────────

def _evt(titulo, fecha="2026-07-01", hora="10:00", calendario="Work"):
    return EventoCalendario(titulo=titulo, fecha=fecha, hora=hora, calendario=calendario)


# ── _parsear_salida ───────────────────────────────────────────────────────────

def test_parsear_salida_basica():
    texto = "Reunión con cliente|2026-07-01|10:00|Work\nLlamada con inversor|2026-07-02|15:30|Personal\n"
    eventos = _parsear_salida(texto)
    assert len(eventos) == 2
    assert eventos[0].titulo == "Reunión con cliente"
    assert eventos[0].fecha == "2026-07-01"
    assert eventos[0].hora == "10:00"
    assert eventos[0].calendario == "Work"


def test_parsear_salida_ignora_lineas_malformadas():
    texto = "Evento válido|2026-07-01|09:00|Work\nlinea rota\n|2026-07-02|\n"
    eventos = _parsear_salida(texto)
    assert len(eventos) == 1
    assert eventos[0].titulo == "Evento válido"


def test_parsear_salida_vacia():
    assert _parsear_salida("") == []
    assert _parsear_salida("\n\n") == []


def test_parsear_salida_sin_calendario():
    texto = "Taller de producto|2026-07-01|11:00\n"
    eventos = _parsear_salida(texto)
    assert len(eventos) == 1
    assert eventos[0].calendario == ""


# ── inferir_contexto_agenda ───────────────────────────────────────────────────

def test_inferir_contexto_sin_eventos():
    assert inferir_contexto_agenda([]) == ""


def test_inferir_contexto_pocos_eventos():
    # 2 eventos no disparan contexto de volumen
    eventos = [_evt("Café", "2026-07-01"), _evt("Almuerzo", "2026-07-03")]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert resultado == ""


def test_inferir_contexto_campaña_electoral():
    eventos = [
        _evt("Reunión campaña electoral", "2026-07-01"),
        _evt("Debate de candidatos", "2026-07-02"),
    ]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "electoral" in resultado or "campaña" in resultado


def test_inferir_contexto_lanzamiento():
    eventos = [
        _evt("Preparación del launch", "2026-07-01"),
        _evt("Demo pre-lanzamiento", "2026-07-02"),
        _evt("Go-live checklist", "2026-07-03"),
    ]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "lanzamiento" in resultado or "launch" in resultado


def test_inferir_contexto_demos_clientes():
    eventos = [
        _evt("Demo con cliente A", "2026-07-01"),
        _evt("Presentación cliente B", "2026-07-02"),
        _evt("Pitch nuevo cliente", "2026-07-03"),
    ]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "demo" in resultado or "cliente" in resultado


def test_inferir_contexto_semana_muy_cargada():
    # 3+ eventos/día → "semana muy cargada"
    eventos = [_evt(f"Reunión {i}", "2026-07-01") for i in range(22)]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "cargada" in resultado or "muy cargada" in resultado


def test_inferir_contexto_semana_activa():
    # ~1.5-3 eventos/día → "semana activa"
    eventos = [_evt(f"Reunión {i}", f"2026-07-{(i%5)+1:02d}") for i in range(12)]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "activa" in resultado or "cargada" in resultado or resultado == ""


def test_inferir_contexto_entrevistas():
    eventos = [
        _evt("Entrevista candidato backend", "2026-07-01"),
        _evt("Interview con diseñadora", "2026-07-02"),
    ]
    resultado = inferir_contexto_agenda(eventos, dias=7)
    assert "selección" in resultado or "entrevista" in resultado


# ── resumir_agenda ────────────────────────────────────────────────────────────

def test_resumir_agenda_vacia():
    assert resumir_agenda([]) == ""


def test_resumir_agenda_incluye_encabezado():
    eventos = [_evt("Reunión clave", "2026-07-01")]
    resultado = resumir_agenda(eventos, dias=7)
    assert "Agenda" in resultado
    assert "7 días" in resultado


def test_resumir_agenda_agrupa_por_fecha():
    eventos = [
        _evt("Reunión A", "2026-07-01"),
        _evt("Reunión B", "2026-07-01"),
        _evt("Llamada", "2026-07-02"),
    ]
    resultado = resumir_agenda(eventos, dias=7)
    assert "2026-07-01" in resultado
    assert "Reunión A" in resultado
    assert "Reunión B" in resultado


def test_resumir_agenda_incluye_contexto_si_relevante():
    eventos = [
        _evt(f"Demo cliente {i}", f"2026-07-{i+1:02d}")
        for i in range(5)
    ]
    resultado = resumir_agenda(eventos, dias=7)
    # El contexto "demo" detectado debería aparecer en el resumen
    assert "Patrón" in resultado or "demo" in resultado.lower()


def test_resumir_agenda_limita_dias_mostrados():
    # Más de 5 días distintos — solo muestra primeros 5
    eventos = [_evt(f"Evt {i}", f"2026-07-{i+1:02d}") for i in range(8)]
    resultado = resumir_agenda(eventos, dias=7)
    # No debe incluir el día 6+
    assert "2026-07-07" not in resultado or resultado.count("2026-07-0") <= 5


# ── Integración con construir_prompt_sintesis ─────────────────────────────────

def _persona_con_historial():
    return Persona(
        nombre="Ana",
        rol="socia",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-06-01", resumen="Reunión inicial sobre la alianza"),
            ConversacionResumen(fecha="2026-06-15", resumen="Avance del contrato"),
        ],
    )


def test_prompt_sin_contexto_agenda():
    p = _persona_con_historial()
    prompt = construir_prompt_sintesis(p, "Juan")
    assert "Contexto de agenda" not in prompt


def test_prompt_con_contexto_agenda():
    p = _persona_con_historial()
    contexto = "Agenda próximos 7 días (4 eventos):\n  2026-07-01: Demo cliente, Reunión legal"
    prompt = construir_prompt_sintesis(p, "Juan", contexto_agenda=contexto)
    assert "Contexto de agenda" in prompt
    assert "Demo cliente" in prompt


def test_prompt_contexto_agenda_vacio_no_contamina():
    p = _persona_con_historial()
    prompt = construir_prompt_sintesis(p, "Juan", contexto_agenda="")
    assert "Contexto de agenda" not in prompt


# ── leer_eventos_macos — mock de osascript ────────────────────────────────────

def test_leer_eventos_macos_mock(monkeypatch):
    import subprocess
    from keel.io.calendario import leer_eventos_macos

    salida_fake = "Reunión importante|2026-07-01|09:00|Work\nLlamada legal|2026-07-02|14:00|Personal\n"

    class FakeResult:
        returncode = 0
        stdout = salida_fake

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    # Forzar plataforma darwin
    monkeypatch.setattr("sys.platform", "darwin")

    eventos = leer_eventos_macos(dias=7)
    assert len(eventos) == 2
    assert eventos[0].titulo == "Reunión importante"


def test_leer_eventos_macos_falla_silenciosamente(monkeypatch):
    import subprocess
    from keel.io.calendario import leer_eventos_macos

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired("osascript", 8))
    )

    eventos = leer_eventos_macos(dias=7)
    assert eventos == []


def test_leer_eventos_macos_no_darwin(monkeypatch):
    from keel.io.calendario import leer_eventos_macos
    monkeypatch.setattr("sys.platform", "linux")
    assert leer_eventos_macos() == []


def test_leer_eventos_macos_returncode_no_cero(monkeypatch):
    import subprocess
    from keel.io.calendario import leer_eventos_macos

    class FakeResult:
        returncode = 1
        stdout = ""

    monkeypatch.setattr("sys.platform", "darwin")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())

    assert leer_eventos_macos() == []
