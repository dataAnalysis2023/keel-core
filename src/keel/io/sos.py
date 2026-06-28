"""Paquete SOS — exportación cifrada de contexto de una persona para uso móvil.

Formato del archivo .ksos:
  - ZIP en memoria con:
      persona.json   — datos completos de la persona
      briefing.md    — resumen legible pre-conversación
      meta.json      — versión, fecha, nombre del perfil
  - El ZIP se cifra con AES-256-GCM usando una clave derivada del passphrase
    (PBKDF2-SHA256, 260 000 iteraciones, sal aleatoria de 16 bytes).
  - Cabecera del archivo: magic KSOS + 16 bytes sal + nonce + ciphertext.

El receptor (app móvil) solo necesita el passphrase para desencriptar.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keel.models.persona import Persona
    from keel.models.perfil import PerfilUsuario

_MAGIC = b"KSOS"
_SALT_SIZE = 16
_NONCE_SIZE = 12
_PBKDF2_ITER = 260_000


@dataclass
class PaqueteSOS:
    persona_json: str       # JSON completo de la Persona
    briefing_md: str        # Briefing en Markdown
    meta: dict              # {version, fecha, perfil_nombre, persona_nombre}


def construir_paquete(
    persona: "Persona",
    perfil: "PerfilUsuario",
    n_recientes: int = 10,
) -> PaqueteSOS:
    """Construye el contenido del paquete SOS sin cifrar."""
    from keel.engine.preparar import briefing_a_markdown

    sintesis_texto = ""
    if persona.narrativa:
        sintesis_texto = persona.narrativa

    briefing = briefing_a_markdown(persona, sintesis=sintesis_texto, n_recientes=n_recientes)

    return PaqueteSOS(
        persona_json=persona.model_dump_json(indent=2),
        briefing_md=briefing,
        meta={
            "version": "1.0",
            "fecha": date.today().isoformat(),
            "perfil_nombre": perfil.nombre,
            "persona_nombre": persona.nombre,
        },
    )


def empaquetar(paquete: PaqueteSOS) -> bytes:
    """Serializa el paquete como ZIP en memoria."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("persona.json", paquete.persona_json)
        zf.writestr("briefing.md", paquete.briefing_md)
        zf.writestr("meta.json", json.dumps(paquete.meta, ensure_ascii=False, indent=2))
    return buf.getvalue()


def cifrar_sos(data: bytes, passphrase: str) -> bytes:
    """Cifra el ZIP con AES-256-GCM derivando la clave del passphrase.

    Formato: KSOS + sal(16) + nonce(12) + ciphertext
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    sal = os.urandom(_SALT_SIZE)
    clave = _derivar_clave(passphrase, sal)
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(clave).encrypt(nonce, data, None)
    return _MAGIC + sal + nonce + ciphertext


def descifrar_sos(data: bytes, passphrase: str) -> bytes:
    """Descifra un archivo .ksos con el passphrase."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not data.startswith(_MAGIC):
        raise ValueError("Archivo no reconocido como paquete SOS (.ksos).")
    offset = len(_MAGIC)
    sal = data[offset: offset + _SALT_SIZE]
    offset += _SALT_SIZE
    nonce = data[offset: offset + _NONCE_SIZE]
    offset += _NONCE_SIZE
    ciphertext = data[offset:]

    clave = _derivar_clave(passphrase, sal)
    try:
        return AESGCM(clave).decrypt(nonce, ciphertext, None)
    except Exception as e:
        raise ValueError("Passphrase incorrecto o archivo corrupto.") from e


def desempaquetar(zip_bytes: bytes) -> PaqueteSOS:
    """Reconstruye un PaqueteSOS desde bytes ZIP."""
    buf = io.BytesIO(zip_bytes)
    with zipfile.ZipFile(buf, "r") as zf:
        persona_json = zf.read("persona.json").decode()
        briefing_md = zf.read("briefing.md").decode()
        meta = json.loads(zf.read("meta.json").decode())
    return PaqueteSOS(
        persona_json=persona_json,
        briefing_md=briefing_md,
        meta=meta,
    )


def guardar_sos(ruta: Path, persona: "Persona", perfil: "PerfilUsuario", passphrase: str) -> int:
    """Construye, empaqueta, cifra y guarda el archivo .ksos. Devuelve tamaño en bytes."""
    paquete = construir_paquete(persona, perfil)
    zip_bytes = empaquetar(paquete)
    cifrado = cifrar_sos(zip_bytes, passphrase)
    ruta.write_bytes(cifrado)
    return len(cifrado)


def _derivar_clave(passphrase: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode(),
        sal,
        _PBKDF2_ITER,
        dklen=32,
    )
