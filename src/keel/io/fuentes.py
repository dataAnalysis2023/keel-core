"""Abstracción de fuentes de mensajes externos.

Cualquier fuente nueva (Telegram, Signal, email, etc.) implementa FuenteMensajes
y queda automáticamente disponible en `keel importar`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MensajeImportado:
    fecha: str      # YYYY-MM-DD
    remitente: str
    texto: str


class FuenteMensajes(ABC):
    """Contrato para fuentes de mensajes externos."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre legible de la fuente (ej: 'WhatsApp Export')."""

    @property
    @abstractmethod
    def extensiones(self) -> list[str]:
        """Extensiones de archivo que esta fuente acepta (ej: ['.txt'])."""

    @abstractmethod
    def leer(self, contenido: str) -> list[MensajeImportado]:
        """Parsea el contenido crudo y devuelve mensajes."""

    def agrupar(
        self,
        mensajes: list[MensajeImportado],
        remitente_externo: str,
    ) -> list[dict]:
        """Agrupa mensajes del remitente por día en entradas de historial.

        Implementación por defecto válida para la mayoría de fuentes.
        Subclases pueden sobreescribir si necesitan agrupación diferente.
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


# ── Implementaciones concretas ────────────────────────────────────────────────

class ExportacionWhatsApp(FuenteMensajes):
    """Exportación de chat de WhatsApp (.txt) — iOS y Android."""

    @property
    def nombre(self) -> str:
        return "WhatsApp Export"

    @property
    def extensiones(self) -> list[str]:
        return [".txt"]

    def leer(self, contenido: str) -> list[MensajeImportado]:
        from keel.io.importar import parsear_whatsapp
        return parsear_whatsapp(contenido)


class TextoPlano(FuenteMensajes):
    """Texto plano: cada párrafo separado por línea en blanco es un mensaje."""

    def __init__(self, fecha_defecto: str) -> None:
        self._fecha = fecha_defecto

    @property
    def nombre(self) -> str:
        return "Texto plano"

    @property
    def extensiones(self) -> list[str]:
        return [".txt", ".md"]

    def leer(self, contenido: str) -> list[MensajeImportado]:
        from keel.io.importar import parsear_texto
        return parsear_texto(contenido, self._fecha)


class CSV(FuenteMensajes):
    """CSV con columnas: fecha, resumen [, temas]."""

    @property
    def nombre(self) -> str:
        return "CSV"

    @property
    def extensiones(self) -> list[str]:
        return [".csv"]

    def leer(self, contenido: str) -> list[MensajeImportado]:
        from keel.io.importar import parsear_csv
        return parsear_csv(contenido)


# ── Registro y detección automática ──────────────────────────────────────────

_FUENTES_POR_FORMATO: dict[str, type[FuenteMensajes]] = {
    "whatsapp": ExportacionWhatsApp,
    "texto": TextoPlano,
    "csv": CSV,
}


def fuente_para_formato(formato: str, fecha_defecto: str = "") -> FuenteMensajes:
    """Devuelve la instancia de FuenteMensajes para el formato dado."""
    cls = _FUENTES_POR_FORMATO.get(formato.lower())
    if cls is None:
        raise ValueError(
            f"Formato '{formato}' desconocido. "
            f"Opciones: {', '.join(_FUENTES_POR_FORMATO)}"
        )
    if cls is TextoPlano:
        return cls(fecha_defecto)
    return cls()


def detectar_fuente(contenido: str, extension: str, fecha_defecto: str = "") -> FuenteMensajes:
    """Detecta automáticamente la fuente correcta según contenido y extensión."""
    import re

    # CSV: extensión o primera línea con comas
    if extension == ".csv":
        return CSV()

    # WhatsApp: patrón de fecha entre corchetes o con guión
    _re_wa = re.compile(
        r"[\[\(]?\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}[,\s]+\d{1,2}:\d{2}"
    )
    if _re_wa.search(contenido[:500]):
        return ExportacionWhatsApp()

    # Fallback: texto plano
    return TextoPlano(fecha_defecto)


def formatos_disponibles() -> list[str]:
    return list(_FUENTES_POR_FORMATO.keys())
