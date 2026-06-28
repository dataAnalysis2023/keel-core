"""Gestión de API keys de proveedores cloud: Keychain (macOS) con fallback a archivo."""

from __future__ import annotations

from pathlib import Path

_SERVICE = "keel-core"
_PROVEEDORES = ("anthropic", "openai")


def _account(proveedor: str) -> str:
    return f"api-key-{proveedor}"


def _archivo_fallback(proveedor: str) -> Path:
    from keel.storage.local import _keel_dir
    return _keel_dir() / f".api-key-{proveedor}"


def guardar_api_key(proveedor: str, key: str) -> None:
    """Guarda la API key en Keychain; fallback a archivo 0600."""
    _validar_proveedor(proveedor)
    guardado = False
    try:
        import keyring
        keyring.set_password(_SERVICE, _account(proveedor), key)
        guardado = True
    except Exception:
        pass

    if not guardado:
        ruta = _archivo_fallback(proveedor)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(key)
        ruta.chmod(0o600)


def obtener_api_key(proveedor: str) -> str | None:
    """Devuelve la API key o None si no está configurada."""
    _validar_proveedor(proveedor)
    try:
        import keyring
        valor = keyring.get_password(_SERVICE, _account(proveedor))
        if valor:
            return valor
    except Exception:
        pass

    ruta = _archivo_fallback(proveedor)
    if ruta.exists():
        return ruta.read_text().strip() or None

    return None


def eliminar_api_key(proveedor: str) -> None:
    """Elimina la API key de Keychain y del archivo de fallback."""
    _validar_proveedor(proveedor)
    try:
        import keyring
        keyring.delete_password(_SERVICE, _account(proveedor))
    except Exception:
        pass

    ruta = _archivo_fallback(proveedor)
    if ruta.exists():
        ruta.unlink()


def _validar_proveedor(proveedor: str) -> None:
    if proveedor not in _PROVEEDORES:
        raise ValueError(
            f"Proveedor '{proveedor}' no soportado. Opciones: {', '.join(_PROVEEDORES)}"
        )


def proveedores_soportados() -> tuple[str, ...]:
    return _PROVEEDORES
