"""Gestión de clave de cifrado: Keychain (macOS) con fallback a archivo 0600."""

import secrets
from pathlib import Path

_SERVICE = "keel-core"
_ACCOUNT = "encryption-key"


def _archivo_clave(keel_dir: Path) -> Path:
    return keel_dir / ".key"


def obtener_clave(keel_dir: Path) -> bytes:
    """Devuelve la clave de cifrado. La crea si no existe."""
    # Intenta Keychain primero
    try:
        import keyring
        valor = keyring.get_password(_SERVICE, _ACCOUNT)
        if valor:
            return bytes.fromhex(valor)
    except Exception:
        pass

    # Fallback: archivo de clave local
    archivo = _archivo_clave(keel_dir)
    if archivo.exists():
        return bytes.fromhex(archivo.read_text().strip())

    return _crear_clave(keel_dir)


def _crear_clave(keel_dir: Path) -> bytes:
    clave = secrets.token_bytes(32)
    hex_clave = clave.hex()

    guardado_en_keychain = False
    try:
        import keyring
        keyring.set_password(_SERVICE, _ACCOUNT, hex_clave)
        guardado_en_keychain = True
    except Exception:
        pass

    if not guardado_en_keychain:
        archivo = _archivo_clave(keel_dir)
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(hex_clave)
        archivo.chmod(0o600)

    return clave


def eliminar_clave(keel_dir: Path) -> None:
    """Elimina la clave de Keychain y del archivo de fallback."""
    try:
        import keyring
        keyring.delete_password(_SERVICE, _ACCOUNT)
    except Exception:
        pass

    archivo = _archivo_clave(keel_dir)
    if archivo.exists():
        archivo.unlink()
