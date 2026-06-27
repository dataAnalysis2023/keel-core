"""Tests de keel.cli.agenda — ver, completar, posponer, borrar, notificar, add."""

import click
import json
import pytest
import keel.storage.local as mod_local

from keel.models.persona import Persona, PromesaPendiente
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, cargar_persona, guardar_perfil

_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    return keel


def _persona_con_promesas(nombre, promesas):
    p = Persona(nombre=nombre, promesas_pendientes=[
        PromesaPendiente(descripcion=d, fecha_compromiso=f)
        for d, f in promesas
    ])
    guardar_persona(p)
    return p


# ── ver --persona ─────────────────────────────────────────────────────────────

def test_ver_filtro_persona(keel_tmp):
    from keel.cli.agenda import ver
    _persona_con_promesas("Ana", [("Enviar doc", "2026-07-01")])
    _persona_con_promesas("Carlos", [("Llamar cliente", "2026-07-05")])
    # Solo debe aparecer Ana
    from typer.testing import CliRunner
    from keel.cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["agenda", "ver", "--persona", "Ana"])
    assert result.exit_code == 0
    assert "Enviar doc" in result.output
    assert "Llamar cliente" not in result.output


def test_ver_filtro_persona_inexistente(keel_tmp):
    from typer.testing import CliRunner
    from keel.cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["agenda", "ver", "--persona", "Nadie"])
    assert result.exit_code == 0
    assert "Sin promesas" in result.output


def test_ver_sin_filtro_muestra_todos(keel_tmp):
    _persona_con_promesas("Ana", [("Tarea Ana", None)])
    _persona_con_promesas("Carlos", [("Tarea Carlos", None)])
    from typer.testing import CliRunner
    from keel.cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["agenda", "ver"])
    assert "Tarea Ana" in result.output
    assert "Tarea Carlos" in result.output


# ── add ───────────────────────────────────────────────────────────────────────

def test_add_sin_fecha(keel_tmp):
    from keel.cli.agenda import add
    add(persona="Ana", descripcion="Enviar resumen", fecha=None)
    p = cargar_persona("Ana")
    assert len(p.promesas_pendientes) == 1
    assert p.promesas_pendientes[0].descripcion == "Enviar resumen"
    assert p.promesas_pendientes[0].fecha_compromiso is None


def test_add_con_fecha(keel_tmp):
    from keel.cli.agenda import add
    add(persona="Carlos", descripcion="Llamar al cliente", fecha="2026-08-01")
    p = cargar_persona("Carlos")
    assert p.promesas_pendientes[0].fecha_compromiso == "2026-08-01"


def test_add_fecha_invalida(keel_tmp):
    from keel.cli.agenda import add
    with pytest.raises(_EXIT):
        add(persona="Luis", descripcion="Algo", fecha="no-es-fecha")


def test_add_acumula_promesas(keel_tmp):
    from keel.cli.agenda import add
    add(persona="Pedro", descripcion="Promesa 1", fecha=None)
    add(persona="Pedro", descripcion="Promesa 2", fecha="2026-09-01")
    p = cargar_persona("Pedro")
    assert len(p.promesas_pendientes) == 2


# ── completar ─────────────────────────────────────────────────────────────────

def test_completar_por_indice(keel_tmp):
    from keel.cli.agenda import completar
    _persona_con_promesas("Carlos", [("Enviar propuesta", "2026-07-01")])
    completar(persona="Carlos", indice=0, descripcion="", forzar=True)
    assert len(cargar_persona("Carlos").promesas_pendientes) == 0


def test_completar_por_descripcion(keel_tmp):
    from keel.cli.agenda import completar
    _persona_con_promesas("Carlos", [("Enviar propuesta", "2026-07-01"), ("Llamar cliente", None)])
    completar(persona="Carlos", indice=None, descripcion="propuesta", forzar=True)
    pendientes = cargar_persona("Carlos").promesas_pendientes
    assert len(pendientes) == 1
    assert pendientes[0].descripcion == "Llamar cliente"


def test_completar_descripcion_ambigua_lanza_exit(keel_tmp):
    from keel.cli.agenda import completar
    _persona_con_promesas("Carlos", [("Enviar A", None), ("Enviar B", None)])
    with pytest.raises(_EXIT):
        completar(persona="Carlos", indice=None, descripcion="Enviar", forzar=True)


def test_completar_indice_fuera_de_rango_lanza_exit(keel_tmp):
    from keel.cli.agenda import completar
    _persona_con_promesas("Carlos", [("Algo", None)])
    with pytest.raises(_EXIT):
        completar(persona="Carlos", indice=5, descripcion="", forzar=True)


def test_completar_sin_indice_ni_descripcion_lanza_exit(keel_tmp):
    from keel.cli.agenda import completar
    _persona_con_promesas("Carlos", [("Algo", None)])
    with pytest.raises(_EXIT):
        completar(persona="Carlos", indice=None, descripcion="", forzar=True)


def test_completar_sin_promesas_exit_cero(keel_tmp):
    from keel.cli.agenda import completar
    guardar_persona(Persona(nombre="Ana"))
    with pytest.raises(_EXIT):
        completar(persona="Ana", indice=0, descripcion="", forzar=True)


# ── posponer ──────────────────────────────────────────────────────────────────

def test_posponer_cambia_fecha(keel_tmp):
    from keel.cli.agenda import posponer
    _persona_con_promesas("María", [("Reunión", "2026-06-28")])
    posponer(persona="María", indice=0, fecha="2026-07-15")
    promesa = cargar_persona("María").promesas_pendientes[0]
    assert promesa.fecha_compromiso == "2026-07-15"


def test_posponer_fecha_invalida_lanza_exit(keel_tmp):
    from keel.cli.agenda import posponer
    _persona_con_promesas("María", [("Reunión", "2026-06-28")])
    with pytest.raises(_EXIT):
        posponer(persona="María", indice=0, fecha="no-es-fecha")


def test_posponer_indice_invalido_lanza_exit(keel_tmp):
    from keel.cli.agenda import posponer
    _persona_con_promesas("María", [("Reunión", "2026-06-28")])
    with pytest.raises(_EXIT):
        posponer(persona="María", indice=99, fecha="2026-07-01")


# ── borrar ────────────────────────────────────────────────────────────────────

def test_borrar_por_indice(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Enviar informe", "2026-07-01"), ("Llamar", None)])
    borrar(persona="María", indice=0, descripcion="", forzar=True)
    p = cargar_persona("María")
    assert len(p.promesas_pendientes) == 1
    assert p.promesas_pendientes[0].descripcion == "Llamar"


def test_borrar_por_descripcion(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Enviar propuesta", "2026-07-01"), ("Llamar", None)])
    borrar(persona="María", indice=None, descripcion="propuesta", forzar=True)
    p = cargar_persona("María")
    assert len(p.promesas_pendientes) == 1
    assert "Llamar" in p.promesas_pendientes[0].descripcion


def test_borrar_indice_invalido(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Única", None)])
    with pytest.raises(_EXIT):
        borrar(persona="María", indice=99, descripcion="", forzar=True)


def test_borrar_sin_coincidencia(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Enviar informe", None)])
    with pytest.raises(_EXIT):
        borrar(persona="María", indice=None, descripcion="xyz_inexistente", forzar=True)


def test_borrar_sin_promesas(keel_tmp):
    from keel.cli.agenda import borrar
    guardar_persona(Persona(nombre="Carlos"))
    with pytest.raises(_EXIT):
        borrar(persona="Carlos", indice=0, descripcion="", forzar=True)


def test_borrar_ambiguo_lanza_exit(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Enviar informe A", None), ("Enviar informe B", None)])
    with pytest.raises(_EXIT):
        borrar(persona="María", indice=None, descripcion="Enviar informe", forzar=True)


def test_borrar_sin_indice_ni_descripcion(keel_tmp):
    from keel.cli.agenda import borrar
    _persona_con_promesas("María", [("Algo", None)])
    with pytest.raises(_EXIT):
        borrar(persona="María", indice=None, descripcion="", forzar=True)


# ── notificar ─────────────────────────────────────────────────────────────────

def test_notificar_no_macos_lanza_exit(keel_tmp, monkeypatch):
    from keel.cli.agenda import notificar
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(_EXIT):
        notificar(dias=2)


def test_notificar_sin_urgentes_no_llama_osascript(keel_tmp, monkeypatch):
    from keel.cli.agenda import notificar
    monkeypatch.setattr("sys.platform", "darwin")

    llamadas = []
    import subprocess as sp
    monkeypatch.setattr(sp, "run", lambda *a, **kw: llamadas.append(a))

    # Promesa lejana — no debe notificar
    _persona_con_promesas("Ana", [("Algo lejano", "2030-01-01")])
    notificar(dias=2)
    assert not any("osascript" in str(c) for c in llamadas)


def test_notificar_urgente_llama_osascript(keel_tmp, monkeypatch):
    from keel.cli.agenda import notificar
    from datetime import date, timedelta
    monkeypatch.setattr("sys.platform", "darwin")

    llamadas = []
    import subprocess as sp
    monkeypatch.setattr(sp, "run", lambda *a, **kw: llamadas.append(a[0]))

    hoy = date.today().isoformat()
    _persona_con_promesas("Carlos", [("Llamar ahora", hoy)])
    notificar(dias=2)

    assert any("osascript" in str(c) for c in llamadas)
