"""Tests de keel.io.obsidian."""

import pytest
from pathlib import Path
from datetime import date

from keel.io.obsidian import (
    escribir_nota,
    exportar_reflexion,
    exportar_persona,
    agregar_a_diario,
    reflexion_path,
    persona_note_path,
    daily_note_path,
)
from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente


# ── escribir_nota ─────────────────────────────────────────────────────────────

def test_crea_directorio_si_no_existe(tmp_path):
    ruta = tmp_path / "sub" / "carpeta" / "nota.md"
    escribir_nota(ruta, "contenido")
    assert ruta.exists()


def test_escribe_contenido(tmp_path):
    ruta = tmp_path / "nota.md"
    escribir_nota(ruta, "Hola mundo")
    assert "Hola mundo" in ruta.read_text()


def test_frontmatter_yaml(tmp_path):
    ruta = tmp_path / "nota.md"
    escribir_nota(ruta, "cuerpo", frontmatter={"tipo": "test", "tags": ["a", "b"]})
    texto = ruta.read_text()
    assert "---" in texto
    assert "tipo: test" in texto
    assert "- a" in texto
    assert "cuerpo" in texto


def test_frontmatter_antes_del_contenido(tmp_path):
    ruta = tmp_path / "nota.md"
    escribir_nota(ruta, "cuerpo", frontmatter={"k": "v"})
    texto = ruta.read_text()
    assert texto.index("---") < texto.index("cuerpo")


# ── exportar_reflexion ────────────────────────────────────────────────────────

def test_exportar_reflexion_crea_archivo(tmp_path):
    ruta = exportar_reflexion("# Reflexión\nContenido", vault=str(tmp_path))
    assert ruta.exists()


def test_exportar_reflexion_ruta_correcta(tmp_path):
    hoy = date.today().isoformat()
    ruta = exportar_reflexion("contenido", vault=str(tmp_path))
    assert f"reflexion-{hoy}" in ruta.name


def test_exportar_reflexion_contiene_frontmatter(tmp_path):
    ruta = exportar_reflexion("contenido", vault=str(tmp_path))
    texto = ruta.read_text()
    assert "tipo: reflexion-semanal" in texto
    assert "tags:" in texto


# ── exportar_persona ─────────────────────────────────────────────────────────

def test_exportar_persona_crea_archivo(tmp_path):
    p = Persona(nombre="Carlos", rol="socio")
    ruta = exportar_persona(p, vault=str(tmp_path))
    assert ruta.exists()


def test_exportar_persona_contiene_nombre(tmp_path):
    p = Persona(nombre="Carlos", rol="socio")
    ruta = exportar_persona(p, vault=str(tmp_path))
    assert "Carlos" in ruta.read_text()


def test_exportar_persona_incluye_conversaciones(tmp_path):
    p = Persona(
        nombre="Ana",
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-06-01", resumen="Hablamos del proyecto", temas=["proyecto"])
        ],
    )
    ruta = exportar_persona(p, vault=str(tmp_path))
    texto = ruta.read_text()
    assert "Hablamos del proyecto" in texto
    assert "proyecto" in texto


def test_exportar_persona_incluye_promesas_como_checkbox(tmp_path):
    p = Persona(
        nombre="Luis",
        promesas_pendientes=[PromesaPendiente(descripcion="Enviar informe", fecha_compromiso="2026-07-01")],
    )
    ruta = exportar_persona(p, vault=str(tmp_path))
    texto = ruta.read_text()
    assert "- [ ] Enviar informe" in texto


def test_exportar_persona_frontmatter(tmp_path):
    p = Persona(nombre="Pedro", rol="cliente")
    ruta = exportar_persona(p, vault=str(tmp_path))
    texto = ruta.read_text()
    assert "tipo: persona-keel" in texto
    assert "nombre: Pedro" in texto


# ── agregar_a_diario ──────────────────────────────────────────────────────────

def test_diario_se_crea_si_no_existe(tmp_path):
    ruta = agregar_a_diario("Mi entrada", vault=str(tmp_path))
    assert ruta.exists()


def test_diario_contiene_entrada(tmp_path):
    ruta = agregar_a_diario("Hablé con Carlos hoy", vault=str(tmp_path))
    assert "Hablé con Carlos hoy" in ruta.read_text()


def test_diario_acumula_entradas(tmp_path):
    agregar_a_diario("Primera entrada", vault=str(tmp_path))
    agregar_a_diario("Segunda entrada", vault=str(tmp_path))
    texto = (daily_note_path(vault=str(tmp_path))).read_text()
    assert "Primera entrada" in texto
    assert "Segunda entrada" in texto


def test_diario_fecha_en_nombre(tmp_path):
    ruta = agregar_a_diario("algo", vault=str(tmp_path))
    assert date.today().isoformat() in ruta.name
