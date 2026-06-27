"""Tests del módulo de cifrado."""

import pytest
import keel.storage.local as mod_local

from keel.security.cifrado import cifrar, descifrar, es_cifrado
from keel.security.llave import obtener_clave, _archivo_clave


# ── cifrado/descifrado ────────────────────────────────────────────────────────

def test_roundtrip_bytes():
    clave = b"a" * 32
    original = b'{"nombre": "Juan"}'
    assert descifrar(cifrar(original, clave), clave) == original


def test_magic_header():
    clave = b"b" * 32
    cifrado = cifrar(b"hola", clave)
    assert es_cifrado(cifrado)


def test_texto_plano_no_es_cifrado():
    assert not es_cifrado(b'{"nombre": "Juan"}')


def test_nonces_distintos_cada_vez():
    clave = b"c" * 32
    data = b"mismo texto"
    assert cifrar(data, clave) != cifrar(data, clave)


def test_descifrar_sin_header_lanza_error():
    with pytest.raises(ValueError, match="cabecera"):
        descifrar(b'{"texto": "plano"}', b"d" * 32)


def test_descifrar_clave_incorrecta_lanza_error():
    clave_buena = b"e" * 32
    clave_mala = b"f" * 32
    cifrado = cifrar(b"secreto", clave_buena)
    with pytest.raises(Exception):
        descifrar(cifrado, clave_mala)


# ── llave ─────────────────────────────────────────────────────────────────────

def test_clave_se_genera_y_persiste(tmp_path, monkeypatch):
    # Bloquea keyring para forzar fallback a archivo
    monkeypatch.setitem(__import__("sys").modules, "keyring", None)

    clave1 = obtener_clave(tmp_path)
    clave2 = obtener_clave(tmp_path)

    assert clave1 == clave2
    assert len(clave1) == 32
    assert _archivo_clave(tmp_path).exists()


def test_archivo_clave_modo_600(tmp_path, monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "keyring", None)
    obtener_clave(tmp_path)
    archivo = _archivo_clave(tmp_path)
    modo = oct(archivo.stat().st_mode)[-3:]
    assert modo == "600"


# ── integración con storage/local ────────────────────────────────────────────

@pytest.fixture
def keel_cifrado(tmp_path, monkeypatch):
    """Directorio ~/.keel/ temporal con cifrado activo."""
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)

    # Activa cifrado sin Keychain
    monkeypatch.setitem(__import__("sys").modules, "keyring", None)
    (keel / ".cifrado").touch()
    yield keel


def test_guardar_y_cargar_perfil_cifrado(keel_cifrado):
    from keel.storage.local import guardar_perfil, cargar_perfil
    from keel.models.perfil import PerfilUsuario

    perfil = PerfilUsuario(nombre="Juan")
    guardar_perfil(perfil)

    # El archivo en disco debe estar cifrado
    ruta = keel_cifrado / "perfil.json"
    assert es_cifrado(ruta.read_bytes())

    # Pero cargar_perfil lo devuelve correctamente
    cargado = cargar_perfil()
    assert cargado.nombre == "Juan"


def test_guardar_y_cargar_persona_cifrada(keel_cifrado):
    from keel.storage.local import guardar_persona, cargar_persona
    from keel.models.persona import Persona

    persona = Persona(nombre="Carlos", rol="socio")
    guardar_persona(persona)

    ruta = keel_cifrado / "personas" / "carlos.json"
    assert es_cifrado(ruta.read_bytes())

    cargada = cargar_persona("Carlos")
    assert cargada.rol == "socio"


def test_sin_cifrado_archivos_son_texto_plano(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr(mod_local, "_KEEL_DIR", keel)

    from keel.storage.local import guardar_perfil
    from keel.models.perfil import PerfilUsuario

    guardar_perfil(PerfilUsuario(nombre="Ana"))
    ruta = keel / "perfil.json"
    assert not es_cifrado(ruta.read_bytes())
    assert b"Ana" in ruta.read_bytes()
