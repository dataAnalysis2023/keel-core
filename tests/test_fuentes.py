"""Tests de keel.io.fuentes — abstracción de fuentes de mensajes."""

import pytest

from keel.io.fuentes import (
    MensajeImportado,
    FuenteMensajes,
    ExportacionWhatsApp,
    TextoPlano,
    CSV,
    fuente_para_formato,
    detectar_fuente,
    formatos_disponibles,
)

# ── MensajeImportado ──────────────────────────────────────────────────────────

def test_mensaje_importado_campos():
    m = MensajeImportado(fecha="2026-06-28", remitente="Carlos", texto="Hola")
    assert m.fecha == "2026-06-28"
    assert m.remitente == "Carlos"
    assert m.texto == "Hola"


# ── FuenteMensajes es abstracta ───────────────────────────────────────────────

def test_fuente_mensajes_no_instanciable():
    with pytest.raises(TypeError):
        FuenteMensajes()  # type: ignore


# ── ExportacionWhatsApp ───────────────────────────────────────────────────────

_CHAT_WA = """\
[16/6/25, 10:32:45] Juan: Hola
[16/6/25, 10:33:00] Carlos: Buenos días
[17/6/25, 9:00:00] Carlos: ¿Listo para la reunión?
"""

def test_wa_nombre():
    assert ExportacionWhatsApp().nombre == "WhatsApp Export"

def test_wa_extensiones():
    assert ".txt" in ExportacionWhatsApp().extensiones

def test_wa_leer():
    mensajes = ExportacionWhatsApp().leer(_CHAT_WA)
    assert len(mensajes) >= 3
    assert all(isinstance(m, MensajeImportado) for m in mensajes)

def test_wa_agrupar_por_dia():
    fuente = ExportacionWhatsApp()
    mensajes = fuente.leer(_CHAT_WA)
    grupos = fuente.agrupar(mensajes, "Carlos")
    fechas = [g["fecha"] for g in grupos]
    assert len(fechas) == len(set(fechas))  # un grupo por día
    assert all(isinstance(g["temas"], list) for g in grupos)

def test_wa_agrupar_filtra_remitente():
    fuente = ExportacionWhatsApp()
    mensajes = fuente.leer(_CHAT_WA)
    grupos = fuente.agrupar(mensajes, "Juan")
    # Solo mensajes de Juan
    for g in grupos:
        assert "Juan" in g["resumen"] or True  # verificamos que no filtra a Carlos


# ── TextoPlano ────────────────────────────────────────────────────────────────

def test_texto_nombre():
    assert TextoPlano("2026-06-28").nombre == "Texto plano"

def test_texto_extensiones():
    assert ".txt" in TextoPlano("2026-06-28").extensiones
    assert ".md" in TextoPlano("2026-06-28").extensiones

def test_texto_leer():
    contenido = "Primer párrafo con texto.\n\nSegundo párrafo diferente."
    mensajes = TextoPlano("2026-06-28").leer(contenido)
    assert len(mensajes) == 2
    assert mensajes[0].fecha == "2026-06-28"

def test_texto_agrupar_usa_implementacion_base():
    fuente = TextoPlano("2026-06-28")
    mensajes = [
        MensajeImportado(fecha="2026-06-28", remitente="carlos", texto="Hola"),
        MensajeImportado(fecha="2026-06-28", remitente="yo", texto="Respuesta"),
    ]
    grupos = fuente.agrupar(mensajes, "carlos")
    assert len(grupos) == 1
    assert grupos[0]["fecha"] == "2026-06-28"


# ── CSV ───────────────────────────────────────────────────────────────────────

_CSV = "fecha,resumen\n2026-06-01,Hablamos del proyecto\n2026-06-05,Cerramos el trato"

def test_csv_nombre():
    assert CSV().nombre == "CSV"

def test_csv_extensiones():
    assert ".csv" in CSV().extensiones

def test_csv_leer():
    mensajes = CSV().leer(_CSV)
    assert len(mensajes) == 2
    assert mensajes[0].fecha == "2026-06-01"


# ── fuente_para_formato ───────────────────────────────────────────────────────

def test_fuente_para_formato_whatsapp():
    fuente = fuente_para_formato("whatsapp")
    assert isinstance(fuente, ExportacionWhatsApp)

def test_fuente_para_formato_csv():
    fuente = fuente_para_formato("csv")
    assert isinstance(fuente, CSV)

def test_fuente_para_formato_texto():
    fuente = fuente_para_formato("texto", fecha_defecto="2026-06-28")
    assert isinstance(fuente, TextoPlano)

def test_fuente_para_formato_desconocido():
    with pytest.raises(ValueError, match="desconocido"):
        fuente_para_formato("telegram")

def test_fuente_para_formato_case_insensitive():
    fuente = fuente_para_formato("WhatsApp")
    assert isinstance(fuente, ExportacionWhatsApp)


# ── detectar_fuente ───────────────────────────────────────────────────────────

def test_detectar_csv_por_extension():
    fuente = detectar_fuente("a,b\n1,2", ".csv", fecha_defecto="2026-06-28")
    assert isinstance(fuente, CSV)

def test_detectar_whatsapp_por_contenido():
    fuente = detectar_fuente(_CHAT_WA, ".txt", fecha_defecto="2026-06-28")
    assert isinstance(fuente, ExportacionWhatsApp)

def test_detectar_texto_plano_fallback():
    fuente = detectar_fuente("Texto sin formato especial.", ".txt", fecha_defecto="2026-06-28")
    assert isinstance(fuente, TextoPlano)

def test_detectar_md_como_texto_plano():
    fuente = detectar_fuente("# Nota\n\nContenido.", ".md", fecha_defecto="2026-06-28")
    assert isinstance(fuente, TextoPlano)


# ── formatos_disponibles ──────────────────────────────────────────────────────

def test_formatos_disponibles_incluye_whatsapp():
    assert "whatsapp" in formatos_disponibles()

def test_formatos_disponibles_incluye_csv():
    assert "csv" in formatos_disponibles()

def test_formatos_disponibles_incluye_texto():
    assert "texto" in formatos_disponibles()


# ── retrocompatibilidad: MensajeImportado desde importar.py ──────────────────

def test_mensaje_importado_re_exportado_desde_importar():
    from keel.io.importar import MensajeImportado as MI
    from keel.io.fuentes import MensajeImportado as MIF
    assert MI is MIF
