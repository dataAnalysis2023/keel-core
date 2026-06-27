"""Tests de keel volcar — engine y CLI."""

import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_persona, guardar_perfil
from keel.engine.volcado import volcar_a_markdown, _icono_promesa

runner = CliRunner(env={"COLUMNS": "200"})
_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    guardar_perfil(PerfilUsuario(nombre="Juan", valores=["claridad", "impacto"]))
    return keel


@pytest.fixture
def persona_completa():
    from datetime import date, timedelta
    vencida = (date.today().replace(day=1)).isoformat()  # primer día del mes actual
    proxima = (date.today() + timedelta(days=2)).isoformat()
    return Persona(
        nombre="Carlos",
        rol="Director de Producto",
        como_nos_conocemos="Cofundador anterior",
        tono_relacional="cercano",
        sensibilidades=["plazos"],
        estado_actual="lanzando v2",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-01-10", resumen="Kick-off", temas=["producto"]),
            ConversacionResumen(fecha="2026-03-01", resumen="Demo cliente", temas=["demo"]),
            ConversacionResumen(fecha="2026-05-15", resumen="Cierre Q1", temas=["legal"]),
            ConversacionResumen(fecha="2026-06-01", resumen="Revisión final", temas=["producto"]),
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Enviar propuesta", fecha_compromiso=proxima),
        ],
    )


# ── _icono_promesa ─────────────────────────────────────────────────────────────

def test_icono_vencida():
    assert _icono_promesa("2020-01-01", "2026-06-27") == "🔴"


def test_icono_proxima():
    from datetime import date, timedelta
    hoy = date.today().isoformat()
    manana = (date.today() + timedelta(days=1)).isoformat()
    assert _icono_promesa(manana, hoy) == "🟡"


def test_icono_lejana():
    assert _icono_promesa("2030-01-01", "2026-06-27") == "🟢"


def test_icono_sin_fecha():
    assert _icono_promesa(None, "2026-06-27") == "🟢"


# ── volcar_a_markdown ─────────────────────────────────────────────────────────

def test_incluye_nombre_perfil(persona_completa):
    perfil = PerfilUsuario(nombre="Juan", valores=["claridad"])
    md = volcar_a_markdown(perfil, [persona_completa])
    assert "Juan" in md


def test_incluye_framing_por_defecto(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa], con_framing=True)
    assert "asistente" in md.lower()


def test_sin_framing_omite_instruccion(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa], con_framing=False)
    assert "asistente personal" not in md.lower()


def test_incluye_datos_persona(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa])
    assert "Carlos" in md
    assert "Director de Producto" in md
    assert "lanzando v2" in md
    assert "plazos" in md


def test_incluye_historial_reciente(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa], recientes=2)
    assert "Revisión final" in md   # más reciente
    assert "Cierre Q1" in md        # segundo más reciente
    assert "Kick-off" not in md     # queda fuera del top 2


def test_incluye_agenda_si_hay_promesas(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa])
    assert "Agenda" in md
    assert "Enviar propuesta" in md


def test_sin_promesas_no_incluye_agenda():
    perfil = PerfilUsuario(nombre="Juan")
    p = Persona(nombre="Ana")
    md = volcar_a_markdown(perfil, [p])
    assert "Agenda" not in md


def test_incluye_valores_perfil():
    perfil = PerfilUsuario(nombre="Juan", valores=["claridad", "impacto"])
    p = Persona(nombre="Ana")
    md = volcar_a_markdown(perfil, [p])
    assert "claridad" in md
    assert "impacto" in md


def test_multiples_personas():
    perfil = PerfilUsuario(nombre="Juan")
    p1 = Persona(nombre="Ana", rol="Abogada")
    p2 = Persona(nombre="Carlos", rol="CTO")
    md = volcar_a_markdown(perfil, [p1, p2])
    assert "Ana" in md
    assert "Carlos" in md
    assert "Abogada" in md
    assert "CTO" in md


# ── CLI ───────────────────────────────────────────────────────────────────────

def test_cli_stdout(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    result = runner.invoke(app, ["volcar"])
    assert result.exit_code == 0
    assert "Carlos" in result.output
    assert "Juan" in result.output


def test_cli_persona_especifica(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    guardar_persona(Persona(nombre="Ana", rol="Abogada"))
    result = runner.invoke(app, ["volcar", "--persona", "Carlos"])
    assert result.exit_code == 0
    assert "Carlos" in result.output
    assert "Ana" not in result.output


def test_cli_sin_framing(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    result = runner.invoke(app, ["volcar", "--sin-framing"])
    assert result.exit_code == 0
    assert "asistente personal" not in result.output.lower()


def test_cli_recientes_controla_historial(keel_tmp, persona_completa):
    guardar_persona(persona_completa)
    result = runner.invoke(app, ["volcar", "--recientes", "1"])
    assert result.exit_code == 0
    assert "Revisión final" in result.output
    assert "Kick-off" not in result.output


def test_cli_sin_personas(keel_tmp):
    result = runner.invoke(app, ["volcar"])
    assert result.exit_code == 0
    assert "No hay personas" in result.output


def test_cli_sin_perfil(keel_tmp, monkeypatch):
    (keel_tmp / "perfil.json").unlink()
    import keel.storage.local as sl
    original = sl.cargar_perfil
    def _fail(): raise FileNotFoundError("no hay perfil")
    monkeypatch.setattr(sl, "cargar_perfil", _fail)
    result = runner.invoke(app, ["volcar"])
    assert result.exit_code != 0


def test_cli_output_a_archivo(keel_tmp, persona_completa, tmp_path):
    guardar_persona(persona_completa)
    dest = tmp_path / "contexto.md"
    result = runner.invoke(app, ["volcar", "--output", str(dest)])
    assert result.exit_code == 0
    assert dest.exists()
    contenido = dest.read_text()
    assert "Carlos" in contenido
    assert "Juan" in contenido


# ── notas en volcado ──────────────────────────────────────────────────────────

def test_incluye_notas_si_se_pasan(persona_completa):
    from keel.models.nota import Nota
    perfil = PerfilUsuario(nombre="Juan")
    notas = [
        Nota(contenido="Decisión importante sobre estrategia", temas=["estrategia"]),
        Nota(contenido="Recordar revisar contrato", temas=["legal"]),
    ]
    md = volcar_a_markdown(perfil, [persona_completa], notas=notas)
    assert "Notas recientes" in md
    assert "Decisión importante" in md
    assert "Recordar revisar contrato" in md


def test_sin_notas_no_incluye_seccion(persona_completa):
    perfil = PerfilUsuario(nombre="Juan")
    md = volcar_a_markdown(perfil, [persona_completa], notas=None)
    assert "Notas recientes" not in md


def test_notas_top_limita(persona_completa):
    from keel.models.nota import Nota
    perfil = PerfilUsuario(nombre="Juan")
    notas = [Nota(contenido=f"Nota {i}", fecha=f"2026-0{i+1}-01") for i in range(5)]
    md = volcar_a_markdown(perfil, [persona_completa], notas=notas, notas_top=2)
    assert md.count("Nota ") <= 2


def test_cli_incluye_notas(keel_tmp, persona_completa):
    from keel.models.nota import Nota
    from keel.storage.local import agregar_nota
    guardar_persona(persona_completa)
    agregar_nota(Nota(contenido="Mi nota de prueba", temas=["test"]))
    result = runner.invoke(app, ["volcar"])
    assert result.exit_code == 0
    assert "Mi nota de prueba" in result.output
    assert "Notas recientes" in result.output


def test_cli_sin_notas_flag(keel_tmp, persona_completa):
    from keel.models.nota import Nota
    from keel.storage.local import agregar_nota
    guardar_persona(persona_completa)
    agregar_nota(Nota(contenido="Nota que no debe aparecer"))
    result = runner.invoke(app, ["volcar", "--sin-notas"])
    assert result.exit_code == 0
    assert "Nota que no debe aparecer" not in result.output
