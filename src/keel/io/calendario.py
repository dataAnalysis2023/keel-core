"""Lectura de eventos del calendario macOS vía osascript.

Lee los eventos de los próximos N días desde la app Calendario (Apple Calendar),
que puede tener sincronizados Google Calendar, iCloud, Outlook, etc.
No requiere OAuth ni credenciales externas.
"""

from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pydantic import BaseModel


class EventoCalendario(BaseModel):
    titulo: str
    fecha: str   # YYYY-MM-DD
    hora: str    # HH:MM o ""
    calendario: str = ""


# Palabras clave que sugieren contextos situacionales específicos
_KEYWORDS_CONTEXTO: list[tuple[list[str], str]] = [
    (["campaña electoral", "electoral", "votación", "elección", "campaign election", "election day"],
     "temporada electoral"),
    (["lanzamiento", "launch", "release", "go-live", "golive"],
     "lanzamiento de producto"),
    (["demo", "demostración", "presentación", "pitch", "client", "cliente"],
     "ciclo de demos con clientes"),
    (["negociación", "propuesta", "contrato", "deal", "cierre"],
     "ciclo de cierre comercial"),
    (["onboarding", "incorporación", "bienvenida", "kickoff", "kick-off"],
     "período de incorporaciones"),
    (["conferencia", "congreso", "summit", "evento", "feria", "festival"],
     "temporada de eventos"),
    (["entrevista", "hiring", "selección", "candidatura", "interview"],
     "proceso de selección"),
]


def leer_eventos_macos(dias: int = 7, timeout: int = 8) -> list[EventoCalendario]:
    """Lee eventos de los próximos N días desde macOS Calendar via osascript.

    Devuelve lista vacía si no es macOS, osascript falla o Calendar no está disponible.
    """
    if sys.platform != "darwin":
        return []

    script = f"""
set diasOffset to {dias}
set hoy to current date
set hoyStr to (year of hoy as string) & "-" & _pad(month of hoy as integer) & "-" & _pad(day of hoy)
set limite to hoy + (diasOffset * days)

on _pad(n)
    if n < 10 then return "0" & (n as string)
    return n as string
end _pad

set salida to ""
tell application "Calendar"
    repeat with cal in every calendar
        set calNombre to name of cal
        set evts to (every event of cal whose start date >= hoy and start date <= limite)
        repeat with evt in evts
            set t to summary of evt
            set d to start date of evt
            set fechaStr to (year of d as string) & "-" & _pad(month of d as integer) & "-" & _pad(day of d)
            set horaStr to _pad(hours of d) & ":" & _pad(minutes of d)
            set salida to salida & t & "|" & fechaStr & "|" & horaStr & "|" & calNombre & "\\n"
        end repeat
    end repeat
end tell
return salida
"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            return []
        return _parsear_salida(result.stdout)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _parsear_salida(texto: str) -> list[EventoCalendario]:
    eventos = []
    for linea in texto.strip().splitlines():
        partes = linea.strip().split("|")
        if len(partes) < 3:
            continue
        titulo = partes[0].strip()
        fecha = partes[1].strip()
        hora = partes[2].strip() if len(partes) > 2 else ""
        calendario = partes[3].strip() if len(partes) > 3 else ""
        if not titulo or not re.match(r"\d{4}-\d{2}-\d{2}", fecha):
            continue
        eventos.append(EventoCalendario(
            titulo=titulo, fecha=fecha, hora=hora, calendario=calendario,
        ))
    return eventos


def inferir_contexto_agenda(eventos: list[EventoCalendario], dias: int = 7) -> str:
    """Produce una descripción del contexto situacional basada en los eventos próximos.

    Devuelve cadena vacía si no hay eventos o el patrón es rutinario.
    """
    if not eventos:
        return ""

    total = len(eventos)
    dias_con_eventos = len({e.fecha for e in eventos})
    titulos_lower = [e.titulo.lower() for e in eventos]
    texto_completo = " ".join(titulos_lower)

    # Detectar contexto específico por keywords
    for keywords, contexto in _KEYWORDS_CONTEXTO:
        if any(kw in texto_completo for kw in keywords):
            ejemplos = [e.titulo for e in eventos if any(kw in e.titulo.lower() for kw in keywords)][:3]
            return f"{contexto} ({', '.join(ejemplos[:2])})"

    # Patrón por volumen
    promedio_dia = total / dias
    if promedio_dia >= 3:
        return f"semana muy cargada — {total} eventos en {dias_con_eventos} día(s)"
    if promedio_dia >= 1.5:
        return f"semana activa — {total} eventos en {dias_con_eventos} día(s)"
    if total <= 2:
        return ""  # demasiado poco para inferir contexto

    return f"{total} eventos en los próximos {dias} días"


def resumir_agenda(eventos: list[EventoCalendario], dias: int = 7) -> str:
    """Genera un resumen de agenda para incluir en el prompt de síntesis."""
    if not eventos:
        return ""

    por_fecha: dict[str, list[str]] = {}
    for e in sorted(eventos, key=lambda x: (x.fecha, x.hora)):
        por_fecha.setdefault(e.fecha, []).append(e.titulo)

    lineas = [f"Agenda próximos {dias} días ({len(eventos)} eventos):"]
    for fecha, titulos in list(por_fecha.items())[:5]:
        titulos_str = ", ".join(titulos[:3])
        if len(titulos) > 3:
            titulos_str += f" (+{len(titulos)-3})"
        lineas.append(f"  {fecha}: {titulos_str}")

    contexto = inferir_contexto_agenda(eventos, dias)
    if contexto:
        lineas.append(f"Patrón detectado: {contexto}")

    return "\n".join(lineas)
