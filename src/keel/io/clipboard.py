"""Canal clipboard — macOS nativo vía pbpaste / pbcopy."""

import subprocess
import sys


def leer() -> str:
    """Lee el texto actual del clipboard. Lanza RuntimeError si falla o está vacío."""
    if sys.platform != "darwin":
        raise RuntimeError("El canal clipboard solo está disponible en macOS.")

    resultado = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"pbpaste falló: {resultado.stderr.strip()}")

    texto = resultado.stdout
    if not texto.strip():
        raise RuntimeError("El clipboard está vacío.")
    return texto


def escribir(texto: str) -> None:
    """Copia texto al clipboard. Lanza RuntimeError si falla."""
    if sys.platform != "darwin":
        raise RuntimeError("El canal clipboard solo está disponible en macOS.")

    resultado = subprocess.run(
        ["pbcopy"],
        input=texto,
        text=True,
        capture_output=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(f"pbcopy falló: {resultado.stderr.strip()}")
