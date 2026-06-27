"""Tests de gestión de personas: renombrar, eliminar, fusionar."""

import pytest
import click
import keel.storage.local as mod_local

_EXIT = (SystemExit, click.exceptions.Exit)
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.storage.local import guardar_persona, cargar_persona


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


def _crear(nombre, conversaciones=None, promesas=None, sensibilidades=None):
    p = Persona(
        nombre=nombre,
        historial_conversaciones=conversaciones or [],
        promesas_pendientes=promesas or [],
        sensibilidades=sensibilidades or [],
    )
    guardar_persona(p)
    return p


def _conv(fecha, resumen, temas=None):
    return ConversacionResumen(fecha=fecha, resumen=resumen, temas=temas or [])


def _prom(desc, fecha=None):
    return PromesaPendiente(descripcion=desc, fecha_compromiso=fecha)


# ── renombrar ─────────────────────────────────────────────────────────────────

def test_renombrar_cambia_archivo(keel_tmp):
    from keel.cli.persona import renombrar
    _crear("Carloss")

    renombrar("Carloss", "Carlos")

    assert (keel_tmp / "personas" / "carlos.json").exists()
    assert not (keel_tmp / "personas" / "carloss.json").exists()


def test_renombrar_actualiza_campo_nombre(keel_tmp):
    from keel.cli.persona import renombrar
    _crear("Carloss")
    renombrar("Carloss", "Carlos")

    cargado = cargar_persona("Carlos")
    assert cargado.nombre == "Carlos"


def test_renombrar_preserva_historial(keel_tmp):
    from keel.cli.persona import renombrar
    _crear("Viejo", conversaciones=[_conv("2026-06-01", "Algo")])
    renombrar("Viejo", "Nuevo")

    cargado = cargar_persona("Nuevo")
    assert len(cargado.historial_conversaciones) == 1


def test_renombrar_inexistente_lanza_exit(keel_tmp):
    from keel.cli.persona import renombrar
    with pytest.raises(_EXIT):
        renombrar("Nadie", "Alguien")


def test_renombrar_a_nombre_existente_lanza_exit(keel_tmp):
    from keel.cli.persona import renombrar
    _crear("Carlos")
    _crear("María")
    with pytest.raises(_EXIT):
        renombrar("Carlos", "María")


# ── eliminar ──────────────────────────────────────────────────────────────────

def test_eliminar_borra_archivo(keel_tmp):
    from keel.cli.persona import eliminar
    _crear("Temporal")
    eliminar("Temporal", forzar=True)
    assert not (keel_tmp / "personas" / "temporal.json").exists()


def test_eliminar_inexistente_lanza_exit(keel_tmp):
    from keel.cli.persona import eliminar
    with pytest.raises(_EXIT):
        eliminar("Fantasma", forzar=True)


# ── fusionar ──────────────────────────────────────────────────────────────────

def test_fusionar_mueve_conversaciones(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Carlos", conversaciones=[_conv("2026-06-01", "Reunión inicial")])
    _crear("Carlos Rodríguez", conversaciones=[_conv("2026-06-10", "Seguimiento")])

    fusionar("Carlos", "Carlos Rodríguez", forzar=True)

    destino = cargar_persona("Carlos Rodríguez")
    assert len(destino.historial_conversaciones) == 2


def test_fusionar_mueve_promesas(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Carlos", promesas=[_prom("Enviar propuesta")])
    _crear("Carlos Rodríguez")

    fusionar("Carlos", "Carlos Rodríguez", forzar=True)

    destino = cargar_persona("Carlos Rodríguez")
    assert len(destino.promesas_pendientes) == 1


def test_fusionar_combina_sensibilidades(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Carlos", sensibilidades=["puntualidad"])
    _crear("Carlos R", sensibilidades=["formalidad"])

    fusionar("Carlos", "Carlos R", forzar=True)

    destino = cargar_persona("Carlos R")
    assert "puntualidad" in destino.sensibilidades
    assert "formalidad" in destino.sensibilidades


def test_fusionar_deduplica_conversaciones(keel_tmp):
    from keel.cli.persona import fusionar
    conv = _conv("2026-06-01", "Misma conversación")
    _crear("Carlos", conversaciones=[conv])
    _crear("Carlos R", conversaciones=[conv])

    fusionar("Carlos", "Carlos R", forzar=True)

    destino = cargar_persona("Carlos R")
    assert len(destino.historial_conversaciones) == 1


def test_fusionar_elimina_origen(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Origen")
    _crear("Destino")
    fusionar("Origen", "Destino", forzar=True)
    assert not (keel_tmp / "personas" / "origen.json").exists()


def test_fusionar_ordena_cronologicamente(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("A", conversaciones=[_conv("2026-06-10", "Tarde")])
    _crear("B", conversaciones=[_conv("2026-06-01", "Temprano")])

    fusionar("A", "B", forzar=True)

    destino = cargar_persona("B")
    fechas = [c.fecha for c in destino.historial_conversaciones]
    assert fechas == sorted(fechas)


def test_fusionar_origen_inexistente_lanza_exit(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Destino")
    with pytest.raises(_EXIT):
        fusionar("Nadie", "Destino", forzar=True)


def test_fusionar_destino_inexistente_lanza_exit(keel_tmp):
    from keel.cli.persona import fusionar
    _crear("Origen")
    with pytest.raises(_EXIT):
        fusionar("Origen", "Nadie", forzar=True)


# ── show enriquecido ───────────────────────────────────────────────────────────

def test_show_persona_completa(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app
    from datetime import date, timedelta

    runner = CliRunner()
    p = Persona(
        nombre="Carlos",
        rol="CTO",
        como_nos_conocemos="Cofundador",
        tono_relacional="cercano",
        sensibilidades=["plazos"],
        estado_actual="lanzando v2",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-05-01", resumen="Kick-off del proyecto", temas=["producto", "roadmap"]),
            ConversacionResumen(fecha="2026-06-01", resumen="Revisión final", temas=["producto", "demo"]),
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso=(date.today() + timedelta(days=5)).isoformat()),
        ],
        ultima_interaccion="2026-06-01",
    )
    guardar_persona(p)

    result = runner.invoke(app, ["persona", "show", "Carlos"])
    assert result.exit_code == 0
    assert "CTO" in result.output
    assert "Cofundador" in result.output
    assert "plazos" in result.output
    assert "lanzando v2" in result.output
    assert "Enviar propuesta" in result.output
    assert "Kick-off del proyecto" in result.output
    assert "producto" in result.output  # tema frecuente


def test_show_persona_vacia(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app

    runner = CliRunner()
    result = runner.invoke(app, ["persona", "show", "Nadie"])
    assert result.exit_code == 0
    assert "Nadie" in result.output


def test_show_raw(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app

    runner = CliRunner()
    guardar_persona(Persona(nombre="Ana", rol="CEO"))
    result = runner.invoke(app, ["persona", "show", "Ana", "--raw"])
    assert result.exit_code == 0
    assert '"rol": "CEO"' in result.output


def test_show_dias_desde_ultima(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app
    from datetime import date, timedelta

    runner = CliRunner()
    hace_10 = (date.today() - timedelta(days=10)).isoformat()
    guardar_persona(Persona(nombre="Pedro", ultima_interaccion=hace_10))
    result = runner.invoke(app, ["persona", "show", "Pedro"])
    assert result.exit_code == 0
    assert "10d" in result.output


def test_show_temas_frecuentes_solo_con_repeticion(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app

    runner = CliRunner()
    guardar_persona(Persona(nombre="María", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="A", temas=["producto", "unico"]),
        ConversacionResumen(fecha="2026-02-01", resumen="B", temas=["producto"]),
    ]))
    result = runner.invoke(app, ["persona", "show", "María"])
    assert result.exit_code == 0
    # "producto" aparece en temas frecuentes (2 veces)
    assert "Temas frecuentes" in result.output
    assert "producto" in result.output
    # "unico" puede aparecer en el historial pero NO en la sección de frecuentes
    # (la sección de frecuentes requiere n > 1 — validado por ausencia del contador ×1)
    assert "×1" not in result.output


def test_show_recientes_limita(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app

    runner = CliRunner()
    guardar_persona(Persona(nombre="Luis", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Primero"),
        ConversacionResumen(fecha="2026-06-01", resumen="Último"),
    ]))
    result = runner.invoke(app, ["persona", "show", "Luis", "--recientes", "1"])
    assert result.exit_code == 0
    assert "Último" in result.output
    assert "Primero" not in result.output
