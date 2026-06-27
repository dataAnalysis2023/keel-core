"""Tests de keel sugerir — motor y CLI."""

import pytest
from datetime import date, timedelta
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil
from keel.engine.sugerencias import sugerir_contactos, sugerencias_a_texto, SugerenciaContacto

runner = CliRunner()
HOY = date.today()


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    return keel


def _persona(nombre, dias_silencio=None, promesas_vencidas=0, promesas_proximas=0, dias_prometida=3):
    promesas = []
    hoy = HOY
    for _ in range(promesas_vencidas):
        promesas.append(PromesaPendiente(
            descripcion=f"Tarea vencida de {nombre}",
            fecha_compromiso=(hoy - timedelta(days=5)).isoformat(),
        ))
    for _ in range(promesas_proximas):
        promesas.append(PromesaPendiente(
            descripcion=f"Tarea próxima de {nombre}",
            fecha_compromiso=(hoy + timedelta(days=dias_prometida)).isoformat(),
        ))
    ultima = (hoy - timedelta(days=dias_silencio)).isoformat() if dias_silencio else None
    return Persona(nombre=nombre, promesas_pendientes=promesas, ultima_interaccion=ultima)


# ── Motor: priorización ───────────────────────────────────────────────────────

def test_promesa_vencida_mayor_urgencia():
    personas = [
        _persona("SilencioLargo", dias_silencio=30),
        _persona("VencidaHoy", promesas_vencidas=1),
    ]
    sugerencias = sugerir_contactos(personas, hoy=HOY, dias_silencio=14, dias_promesa=7)
    assert sugerencias[0].persona == "VencidaHoy"


def test_promesa_proxima_mayor_que_silencio():
    personas = [
        _persona("Silencio", dias_silencio=20),
        _persona("Proxima", promesas_proximas=1, dias_prometida=2),
    ]
    sugerencias = sugerir_contactos(personas, hoy=HOY, dias_silencio=14, dias_promesa=7)
    assert sugerencias[0].persona == "Proxima"


def test_silencio_menor_al_umbral_no_aparece():
    personas = [_persona("Reciente", dias_silencio=5)]
    sugerencias = sugerir_contactos(personas, hoy=HOY, dias_silencio=14)
    assert len(sugerencias) == 0


def test_sin_contactos_urgentes():
    personas = [Persona(nombre="Ana")]
    sugerencias = sugerir_contactos(personas, hoy=HOY)
    assert sugerencias == []


def test_top_limita_resultados():
    personas = [
        _persona("A", promesas_vencidas=1),
        _persona("B", promesas_vencidas=1),
        _persona("C", dias_silencio=20),
    ]
    sugerencias = sugerir_contactos(personas, hoy=HOY, top=2, dias_silencio=14, dias_promesa=7)
    assert len(sugerencias) <= 2


def test_razones_incluyen_descripcion():
    personas = [_persona("Carlos", promesas_vencidas=1)]
    sugerencias = sugerir_contactos(personas, hoy=HOY, dias_silencio=14, dias_promesa=7)
    assert any("Tarea vencida de Carlos" in r for r in sugerencias[0].razones)


def test_razones_incluyen_dias_silencio():
    personas = [_persona("Ana", dias_silencio=20)]
    sugerencias = sugerir_contactos(personas, hoy=HOY, dias_silencio=14, dias_promesa=7)
    assert any("sin contacto" in r.lower() for r in sugerencias[0].razones)


def test_temas_frecuentes_en_razones():
    p = Persona(
        nombre="Pedro",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-01-01", resumen="R", temas=["producto"]),
            ConversacionResumen(fecha="2026-02-01", resumen="R2", temas=["producto"]),
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Algo vencido", fecha_compromiso=(HOY - timedelta(days=2)).isoformat()),
        ],
    )
    sugerencias = sugerir_contactos([p], hoy=HOY, dias_silencio=14, dias_promesa=7)
    assert any("producto" in r for r in sugerencias[0].razones)


# ── Motor: texto ──────────────────────────────────────────────────────────────

def test_sugerencias_a_texto_sin_sugerencias():
    texto = sugerencias_a_texto([])
    assert "Sin contactos urgentes" in texto


def test_sugerencias_a_texto_con_datos():
    s = SugerenciaContacto(persona="Carlos", razones=["Promesa vencida"], urgencia=100)
    texto = sugerencias_a_texto([s])
    assert "Carlos" in texto
    assert "Promesa vencida" in texto
    assert "1." in texto


# ── CLI ────────────────────────────────────────────────────────────────────────

def test_sugerir_sin_urgencias(keel_tmp):
    guardar_persona(Persona(nombre="Ana"))
    result = runner.invoke(app, ["sugerir", "--sin-llm"])
    assert result.exit_code == 0
    assert "Sin contactos urgentes" in result.output


def test_sugerir_con_promesa_vencida(keel_tmp):
    guardar_persona(_persona("Carlos", promesas_vencidas=1))
    result = runner.invoke(app, ["sugerir", "--sin-llm"])
    assert result.exit_code == 0
    assert "Carlos" in result.output
    assert "vencida" in result.output.lower()


def test_sugerir_sin_personas(keel_tmp):
    result = runner.invoke(app, ["sugerir", "--sin-llm"])
    assert result.exit_code == 0
    assert "No hay personas" in result.output


def test_sugerir_top_limita(keel_tmp):
    for nombre in ["A", "B", "C"]:
        guardar_persona(_persona(nombre, promesas_vencidas=1))
    result = runner.invoke(app, ["sugerir", "--sin-llm", "--top", "2"])
    assert result.exit_code == 0
    # Solo deben aparecer 2 entradas numeradas
    assert "1." in result.output
    assert "2." in result.output
    assert "3." not in result.output


def test_sugerir_clipboard(keel_tmp, monkeypatch):
    guardar_persona(_persona("Ana", promesas_vencidas=1))
    escritos = []
    monkeypatch.setattr("keel.io.clipboard.escribir", lambda t: escritos.append(t))
    result = runner.invoke(app, ["sugerir", "--sin-llm", "--clipboard"])
    assert result.exit_code == 0
    assert len(escritos) == 1
    assert "Ana" in escritos[0]


def test_sugerir_usa_config_dias(keel_tmp, monkeypatch):
    from keel.models.config import ConfigKeel
    from keel.storage.local import guardar_config
    guardar_config(ConfigKeel(dias_silencio=5))
    # Con umbral de 5 días, 7 días de silencio ya debe aparecer
    guardar_persona(_persona("RecienteConUmbralBajo", dias_silencio=7))
    result = runner.invoke(app, ["sugerir", "--sin-llm"])
    assert result.exit_code == 0
    assert "RecienteConUmbralBajo" in result.output
