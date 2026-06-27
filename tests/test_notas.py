"""Tests de keel notas — modelo, storage, engine y CLI."""

import json
import click
import pytest
import keel.storage.local as mod_local
from typer.testing import CliRunner
from keel.cli.main import app
from keel.models.nota import Nota
from keel.models.perfil import PerfilUsuario
from keel.storage.local import guardar_perfil, cargar_notas, guardar_notas, agregar_nota, eliminar_nota
from keel.engine.busqueda import buscar_notas

runner = CliRunner(env={"COLUMNS": "200"})
_EXIT = (SystemExit, click.exceptions.Exit)


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)
    guardar_perfil(PerfilUsuario(nombre="Juan"))
    return keel


# ── Modelo ────────────────────────────────────────────────────────────────────

def test_nota_id_generado():
    n = Nota(contenido="algo")
    assert len(n.id) == 8


def test_nota_fecha_hoy():
    from datetime import date
    n = Nota(contenido="algo")
    assert n.fecha == date.today().isoformat()


def test_nota_temas_opcionales():
    n = Nota(contenido="algo")
    assert n.temas == []


# ── Storage ───────────────────────────────────────────────────────────────────

def test_cargar_notas_vacio(keel_tmp):
    assert cargar_notas() == []


def test_agregar_y_cargar(keel_tmp):
    agregar_nota(Nota(contenido="Primera nota"))
    agregar_nota(Nota(contenido="Segunda nota"))
    notas = cargar_notas()
    assert len(notas) == 2
    assert notas[0].contenido == "Primera nota"


def test_eliminar_nota(keel_tmp):
    n = Nota(contenido="Para borrar")
    agregar_nota(n)
    assert eliminar_nota(n.id) is True
    assert cargar_notas() == []


def test_eliminar_nota_inexistente(keel_tmp):
    assert eliminar_nota("noexiste") is False


def test_guardar_y_cargar_temas(keel_tmp):
    n = Nota(contenido="Con temas", temas=["legal", "producto"])
    agregar_nota(n)
    notas = cargar_notas()
    assert notas[0].temas == ["legal", "producto"]


# ── Engine buscar_notas ───────────────────────────────────────────────────────

def test_buscar_keyword_encuentra():
    notas = [
        Nota(contenido="Reunión sobre el proyecto legal", temas=["legal"]),
        Nota(contenido="Idea de nuevo producto", temas=["producto"]),
    ]
    res = buscar_notas("legal", notas)
    assert len(res) == 1
    assert "legal" in res[0]["resumen"].lower()


def test_buscar_keyword_persona_es_nota():
    notas = [Nota(contenido="nota de prueba", temas=[])]
    res = buscar_notas("prueba", notas)
    assert res[0]["persona"] == "[nota]"


def test_buscar_keyword_por_tema():
    notas = [Nota(contenido="contenido cualquiera", temas=["estrategia"])]
    res = buscar_notas("estrategia", notas)
    assert len(res) == 1


def test_buscar_sin_resultados():
    notas = [Nota(contenido="texto irrelevante")]
    res = buscar_notas("xyz123inexistente", notas)
    assert res == []


def test_buscar_top_limita():
    notas = [Nota(contenido=f"nota {i} sobre producto") for i in range(10)]
    res = buscar_notas("producto", notas, top=3)
    assert len(res) <= 3


# ── CLI keel notas add ────────────────────────────────────────────────────────

def test_cli_add_basico(keel_tmp):
    result = runner.invoke(app, ["notas", "add", "Recordar llamar al cliente"])
    assert result.exit_code == 0
    assert "✓" in result.output
    assert len(cargar_notas()) == 1


def test_cli_add_con_temas(keel_tmp):
    result = runner.invoke(app, ["notas", "add", "Idea importante", "--temas", "producto,legal"])
    assert result.exit_code == 0
    n = cargar_notas()[0]
    assert n.temas == ["producto", "legal"]


def test_cli_add_acumula(keel_tmp):
    runner.invoke(app, ["notas", "add", "Primera"])
    runner.invoke(app, ["notas", "add", "Segunda"])
    assert len(cargar_notas()) == 2


# ── CLI keel notas ver ────────────────────────────────────────────────────────

def test_cli_ver_vacio(keel_tmp):
    result = runner.invoke(app, ["notas", "ver"])
    assert result.exit_code == 0
    assert "No hay notas" in result.output


def test_cli_ver_muestra_notas(keel_tmp):
    agregar_nota(Nota(contenido="Mi idea de negocio"))
    result = runner.invoke(app, ["notas", "ver"])
    assert result.exit_code == 0
    assert "Mi idea de negocio" in result.output


def test_cli_ver_top_limita(keel_tmp):
    for i in range(5):
        agregar_nota(Nota(contenido=f"Nota {i}", fecha=f"2026-0{i+1}-01"))
    result = runner.invoke(app, ["notas", "ver", "--top", "2"])
    assert result.exit_code == 0
    # Verifica que no aparecen más de 2 (aproximado — busca filas)
    assert result.output.count("2026-0") <= 2


# ── CLI keel notas buscar ─────────────────────────────────────────────────────

def test_cli_buscar_encuentra(keel_tmp):
    agregar_nota(Nota(contenido="Tenemos reunión sobre estrategia digital"))
    result = runner.invoke(app, ["notas", "buscar", "estrategia", "--sin-vectores"])
    assert result.exit_code == 0
    assert "estrategia" in result.output.lower()


def test_cli_buscar_sin_resultados(keel_tmp):
    result = runner.invoke(app, ["notas", "buscar", "xyz999", "--sin-vectores"])
    assert result.exit_code == 0
    assert "Sin resultados" in result.output


# ── CLI keel notas editar ─────────────────────────────────────────────────────

def test_cli_editar_contenido(keel_tmp):
    n = Nota(contenido="Contenido original")
    agregar_nota(n)
    result = runner.invoke(app, ["notas", "editar", n.id, "--contenido", "Contenido actualizado"])
    assert result.exit_code == 0
    assert "✓" in result.output
    notas = cargar_notas()
    assert notas[0].contenido == "Contenido actualizado"


def test_cli_editar_temas(keel_tmp):
    n = Nota(contenido="Mi nota", temas=["viejo"])
    agregar_nota(n)
    result = runner.invoke(app, ["notas", "editar", n.id, "--temas", "nuevo,legal"])
    assert result.exit_code == 0
    notas = cargar_notas()
    assert notas[0].temas == ["nuevo", "legal"]


def test_cli_editar_preserva_fecha(keel_tmp):
    n = Nota(contenido="Nota con fecha", fecha="2026-01-15")
    agregar_nota(n)
    runner.invoke(app, ["notas", "editar", n.id, "--contenido", "Nuevo contenido"])
    notas = cargar_notas()
    assert notas[0].fecha == "2026-01-15"


def test_cli_editar_contenido_y_temas(keel_tmp):
    n = Nota(contenido="Viejo", temas=["x"])
    agregar_nota(n)
    result = runner.invoke(app, ["notas", "editar", n.id, "--contenido", "Nuevo", "--temas", "a,b"])
    assert result.exit_code == 0
    notas = cargar_notas()
    assert notas[0].contenido == "Nuevo"
    assert notas[0].temas == ["a", "b"]


def test_cli_editar_inexistente(keel_tmp):
    result = runner.invoke(app, ["notas", "editar", "noexiste", "--contenido", "x"])
    assert result.exit_code != 0


# ── CLI keel notas borrar ─────────────────────────────────────────────────────

def test_cli_borrar_forzar(keel_tmp):
    n = Nota(contenido="Nota a borrar")
    agregar_nota(n)
    result = runner.invoke(app, ["notas", "borrar", n.id, "--forzar"])
    assert result.exit_code == 0
    assert "✓" in result.output
    assert cargar_notas() == []


def test_cli_borrar_inexistente(keel_tmp):
    result = runner.invoke(app, ["notas", "borrar", "noexiste", "--forzar"])
    assert result.exit_code != 0


# ── Integración pregunta global ───────────────────────────────────────────────

def test_pregunta_global_incluye_notas(keel_tmp, monkeypatch):
    agregar_nota(Nota(contenido="Decisión sobre el proyecto hasta agosto", temas=["proyecto"]))
    import keel.llm.ollama as mod_ollama

    class FakeOllama:
        def __init__(self, **kw): pass
        def disponible(self): return True
        def generar(self, prompt): return "respuesta generada"

    monkeypatch.setattr(mod_ollama, "OllamaLLM", FakeOllama)
    result = runner.invoke(app, ["pregunta", "proyecto", "--sin-vectores"])
    assert result.exit_code == 0
    # La nota aparece como contexto: el mensaje "1 fragmento(s)" prueba que se incluyó
    assert "1 fragmento" in result.output
