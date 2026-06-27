"""Cifrado AES-GCM para archivos de usuario."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"KEEL"
_NONCE_SIZE = 12
_HEADER_SIZE = len(_MAGIC) + _NONCE_SIZE


def cifrar(data: bytes, clave: bytes) -> bytes:
    """Cifra bytes con AES-256-GCM. Formato: MAGIC + nonce + ciphertext."""
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = AESGCM(clave).encrypt(nonce, data, None)
    return _MAGIC + nonce + ciphertext


def descifrar(data: bytes, clave: bytes) -> bytes:
    """Descifra bytes cifrados con `cifrar()`."""
    if not es_cifrado(data):
        raise ValueError("El archivo no tiene cabecera de cifrado KEEL.")
    nonce = data[len(_MAGIC): _HEADER_SIZE]
    ciphertext = data[_HEADER_SIZE:]
    return AESGCM(clave).decrypt(nonce, ciphertext, None)


def es_cifrado(data: bytes) -> bool:
    return data[:len(_MAGIC)] == _MAGIC
