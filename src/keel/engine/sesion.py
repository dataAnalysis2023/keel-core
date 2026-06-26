"""Lógica de una sesión de conversación completa.

Separado del CLI para ser testeable sin TTY.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from keel.engine.presencia import analizar_tono, ResultadoTono
from keel.engine.respuesta import generar_sugerencia
from keel.models.perfil import PerfilUsuario
from keel.models.persona import Persona, ConversacionResumen

if TYPE_CHECKING:
    from keel.llm.base import LLMBase
    from keel.embedder.base import EmbedderBase


@dataclass
class ResultadoSesion:
    sugerencia: str
    tono: ResultadoTono
    modo_contexto: str  # "semántico" | "cronológico" | "sin historial"


def ejecutar(
    perfil: PerfilUsuario,
    persona: Persona,
    mensaje: str,
    llm: "LLMBase",
    embedder: "EmbedderBase | None" = None,
) -> ResultadoSesion:
    """Genera la sugerencia y recopila metadatos de la sesión."""
    tono = analizar_tono(mensaje)

    if embedder:
        modo = "semántico"
    elif persona.historial_conversaciones:
        modo = "cronológico"
    else:
        modo = "sin historial"

    sugerencia = generar_sugerencia(perfil, persona, mensaje, llm, embedder)

    return ResultadoSesion(sugerencia=sugerencia, tono=tono, modo_contexto=modo)


def generar_resumen_automatico(mensaje: str, respuesta: str) -> str:
    """Resumen breve para el historial: primeras palabras del mensaje."""
    texto = mensaje.replace("\n", " ").strip()
    return texto[:80] + ("…" if len(texto) > 80 else "")


def guardar(
    persona: Persona,
    resumen: str,
    temas: list[str],
    embedder: "EmbedderBase | None" = None,
) -> None:
    """Persiste la sesión en JSON y, si hay embedder, en LanceDB."""
    from keel.storage.local import guardar_persona
    from keel.storage.vectorial import indexar_conversacion

    hoy = date.today().isoformat()
    persona.historial_conversaciones.append(
        ConversacionResumen(fecha=hoy, resumen=resumen, temas=temas)
    )
    persona.ultima_interaccion = hoy
    guardar_persona(persona)

    if embedder:
        try:
            indexar_conversacion(persona.nombre, hoy, resumen, temas, embedder)
        except Exception:
            pass


def abrir_en_editor(texto: str) -> str:
    """Abre el texto en $EDITOR y devuelve el contenido editado."""
    import os
    import subprocess
    import tempfile

    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="keel_",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(texto)
        tmpfile = f.name

    try:
        subprocess.run([editor, tmpfile], check=False)
        with open(tmpfile, encoding="utf-8") as f:
            return f.read().strip()
    finally:
        os.unlink(tmpfile)


def leer_mensaje_stdin() -> str:
    """Lee un mensaje multilinea de stdin (piped o interactivo)."""
    import sys

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    # Modo interactivo: leer hasta línea vacía o Ctrl+D
    lineas: list[str] = []
    try:
        while True:
            linea = input()
            if linea == "" and lineas and lineas[-1] == "":
                break
            lineas.append(linea)
    except EOFError:
        pass

    return "\n".join(lineas).strip()
