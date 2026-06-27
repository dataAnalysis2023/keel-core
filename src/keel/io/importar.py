"""Parsers para importar historial de conversaciones externas."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MensajeImportado:
    fecha: str          # YYYY-MM-DD
    remitente: str
    texto: str


# ── WhatsApp ──────────────────────────────────────────────────────────────────
# Formatos soportados:
#   [16/6/25, 10:32:45] Juan: Hola           (iOS, con corchetes)
#   16/6/25, 10:32 - Juan: Hola              (Android, con guión)

_RE_WHATSAPP = re.compile(
    r"[\[\(]?"
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})"  # fecha
    r"[,\s]+"
    r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[aApP][mM])?)"  # hora
    r"[\]\)]?"
    r"[\s\-–]+?"
    r"([^:]+?)"                               # remitente
    r":\s"
    r"(.+)",                                  # texto
    re.MULTILINE,
)

_MENSAJES_SISTEMA = frozenset([
    "Los mensajes y las llamadas están cifrados",
    "Messages and calls are end-to-end encrypted",
    "omitted",
    "<Media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "document omitted",
])


def parsear_whatsapp(contenido: str) -> list[MensajeImportado]:
    """Parsea un archivo de exportación de WhatsApp (.txt)."""
    mensajes = []

    for match in _RE_WHATSAPP.finditer(contenido):
        fecha_raw, _, remitente, texto = match.groups()
        texto = texto.strip()

        if any(s.lower() in texto.lower() for s in _MENSAJES_SISTEMA):
            continue
        if not texto or len(texto) < 3:
            continue

        fecha = _normalizar_fecha(fecha_raw)
        if not fecha:
            continue

        mensajes.append(MensajeImportado(
            fecha=fecha,
            remitente=remitente.strip(),
            texto=texto,
        ))

    return mensajes


def _normalizar_fecha(fecha_raw: str) -> str | None:
    """Convierte fecha en varios formatos a YYYY-MM-DD."""
    separador = re.search(r"[/\-.]", fecha_raw)
    if not separador:
        return None
    sep = separador.group()
    partes = fecha_raw.split(sep)
    if len(partes) != 3:
        return None

    d, m, a = partes
    if len(a) == 2:
        a = f"20{a}"

    try:
        return datetime(int(a), int(m), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


# ── Texto plano ───────────────────────────────────────────────────────────────

def parsear_texto(contenido: str, fecha_defecto: str) -> list[MensajeImportado]:
    """Parsea texto plano: cada párrafo (separado por línea en blanco) es un mensaje."""
    parrafos = [p.strip() for p in re.split(r"\n{2,}", contenido) if p.strip()]
    return [
        MensajeImportado(fecha=fecha_defecto, remitente="desconocido", texto=p)
        for p in parrafos
        if len(p) >= 5
    ]


# ── CSV ───────────────────────────────────────────────────────────────────────

def parsear_csv(contenido: str) -> list[MensajeImportado]:
    """Parsea CSV con columnas: fecha, resumen [, temas].

    Primera fila puede ser encabezado (se detecta automáticamente).
    """
    import csv
    import io

    mensajes = []
    reader = csv.reader(io.StringIO(contenido))
    primera = True

    for fila in reader:
        if not fila:
            continue
        if primera:
            primera = False
            if fila[0].lower() in ("fecha", "date", "día"):
                continue  # saltar encabezado

        if len(fila) < 2:
            continue

        fecha = fila[0].strip()
        texto = fila[1].strip()
        if not fecha or not texto:
            continue

        mensajes.append(MensajeImportado(
            fecha=fecha,
            remitente="importado",
            texto=texto,
        ))

    return mensajes


# ── Agrupación en resúmenes ───────────────────────────────────────────────────

def agrupar_en_dia(
    mensajes: list[MensajeImportado],
    remitente_externo: str,
) -> list[dict]:
    """Agrupa mensajes por día en resúmenes para guardar en historial.

    Solo retiene mensajes del remitente externo (no los propios).
    Devuelve lista de {fecha, resumen, temas}.
    """
    por_dia: dict[str, list[str]] = {}

    for m in mensajes:
        if m.remitente.lower() == remitente_externo.lower():
            por_dia.setdefault(m.fecha, []).append(m.texto)

    resultado = []
    for fecha, textos in sorted(por_dia.items()):
        resumen = textos[0][:120].replace("\n", " ")
        if len(textos) > 1:
            resumen += f" [+{len(textos) - 1} mensajes]"
        resultado.append({"fecha": fecha, "resumen": resumen, "temas": []})

    return resultado
