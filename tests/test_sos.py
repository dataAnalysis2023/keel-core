"""Tests de keel.io.sos — paquete SOS cifrado para uso móvil."""

import json
import zipfile
import io
import pytest

from keel.io.sos import (
    construir_paquete,
    empaquetar,
    cifrar_sos,
    descifrar_sos,
    desempaquetar,
    guardar_sos,
    PaqueteSOS,
)
from keel.models.persona import Persona, ConversacionResumen
from keel.models.perfil import PerfilUsuario


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _persona() -> Persona:
    p = Persona(nombre="Carlos")
    p.historial_conversaciones = [
        ConversacionResumen(
            fecha="2026-06-01",
            resumen="Hablamos del proyecto",
            temas=["proyecto"],
        )
    ]
    p.narrativa = "Carlos es un colaborador cercano con quien trabajo hace dos años."
    p.tipo_relacion = "colaborador"
    return p


def _perfil() -> PerfilUsuario:
    return PerfilUsuario(nombre="Juan Diego")


# ── construir_paquete ─────────────────────────────────────────────────────────

def test_construir_paquete_campos():
    paquete = construir_paquete(_persona(), _perfil())
    assert isinstance(paquete, PaqueteSOS)
    assert "Carlos" in paquete.persona_json
    assert "Carlos" in paquete.briefing_md
    assert paquete.meta["persona_nombre"] == "Carlos"
    assert paquete.meta["perfil_nombre"] == "Juan Diego"
    assert paquete.meta["version"] == "1.0"
    assert "fecha" in paquete.meta

def test_construir_paquete_narrativa_en_briefing():
    paquete = construir_paquete(_persona(), _perfil())
    assert "colaborador" in paquete.briefing_md or "Carlos" in paquete.briefing_md


# ── empaquetar / desempaquetar ────────────────────────────────────────────────

def test_empaquetar_es_zip_valido():
    paquete = construir_paquete(_persona(), _perfil())
    zip_bytes = empaquetar(paquete)
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        nombres = zf.namelist()
    assert "persona.json" in nombres
    assert "briefing.md" in nombres
    assert "meta.json" in nombres

def test_desempaquetar_roundtrip():
    paquete = construir_paquete(_persona(), _perfil())
    zip_bytes = empaquetar(paquete)
    recuperado = desempaquetar(zip_bytes)
    assert recuperado.meta["persona_nombre"] == "Carlos"
    assert "Carlos" in recuperado.persona_json

def test_persona_json_valido():
    paquete = construir_paquete(_persona(), _perfil())
    zip_bytes = empaquetar(paquete)
    recuperado = desempaquetar(zip_bytes)
    datos = json.loads(recuperado.persona_json)
    assert datos["nombre"] == "Carlos"


# ── cifrar_sos / descifrar_sos ────────────────────────────────────────────────

def test_cifrar_descifrar_roundtrip():
    data = b"datos secretos del SOS"
    passphrase = "mi-passphrase-seguro"
    cifrado = cifrar_sos(data, passphrase)
    descifrado = descifrar_sos(cifrado, passphrase)
    assert descifrado == data

def test_cifrado_empieza_con_magic():
    cifrado = cifrar_sos(b"test", "pass")
    assert cifrado[:4] == b"KSOS"

def test_cifrado_passphrase_incorrecto():
    cifrado = cifrar_sos(b"secreto", "correcto")
    with pytest.raises(ValueError, match="Passphrase incorrecto"):
        descifrar_sos(cifrado, "incorrecto")

def test_cifrado_archivo_invalido():
    with pytest.raises(ValueError, match="no reconocido"):
        descifrar_sos(b"datos-sin-magic", "pass")

def test_dos_cifrados_difieren():
    # Cada cifrado usa sal y nonce aleatorios
    data = b"mismo contenido"
    c1 = cifrar_sos(data, "pass")
    c2 = cifrar_sos(data, "pass")
    assert c1 != c2

def test_descifrar_produce_zip_valido():
    paquete = construir_paquete(_persona(), _perfil())
    zip_bytes = empaquetar(paquete)
    cifrado = cifrar_sos(zip_bytes, "mi-pass")
    recuperado_zip = descifrar_sos(cifrado, "mi-pass")
    recuperado = desempaquetar(recuperado_zip)
    assert recuperado.meta["persona_nombre"] == "Carlos"


# ── guardar_sos ───────────────────────────────────────────────────────────────

def test_guardar_sos_crea_archivo(tmp_path):
    ruta = tmp_path / "carlos.ksos"
    tamanio = guardar_sos(ruta, _persona(), _perfil(), "pass-test")
    assert ruta.exists()
    assert tamanio > 0
    assert ruta.stat().st_size == tamanio

def test_guardar_sos_contenido_descifrable(tmp_path):
    ruta = tmp_path / "carlos.ksos"
    guardar_sos(ruta, _persona(), _perfil(), "pass-test")
    cifrado = ruta.read_bytes()
    zip_bytes = descifrar_sos(cifrado, "pass-test")
    paquete = desempaquetar(zip_bytes)
    assert paquete.meta["persona_nombre"] == "Carlos"

def test_guardar_sos_tamanio_razonable(tmp_path):
    ruta = tmp_path / "carlos.ksos"
    tamanio = guardar_sos(ruta, _persona(), _perfil(), "pass")
    assert tamanio < 50 * 1024  # menos de 50 KB por persona
