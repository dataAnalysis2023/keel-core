"""Tests de keel.io.importar — parsers de historial externo."""

from datetime import date

from keel.io.importar import (
    parsear_whatsapp,
    parsear_texto,
    parsear_csv,
    agrupar_en_dia,
    _normalizar_fecha,
)


# ── _normalizar_fecha ─────────────────────────────────────────────────────────

def test_fecha_formato_dia_mes_anio_corto():
    assert _normalizar_fecha("16/6/25") == "2025-06-16"

def test_fecha_formato_dia_mes_anio_largo():
    assert _normalizar_fecha("16/06/2025") == "2025-06-16"

def test_fecha_con_guion():
    assert _normalizar_fecha("16-06-25") == "2025-06-16"

def test_fecha_invalida():
    assert _normalizar_fecha("notafecha") is None

def test_fecha_dia_fuera_de_rango():
    assert _normalizar_fecha("32/01/25") is None


# ── parsear_whatsapp ──────────────────────────────────────────────────────────

CHAT_IOS = """\
[16/6/25, 10:32:45] Juan: Hola, ¿cómo estás?
[16/6/25, 10:33:00] Carlos: Bien, ¿y tú?
[16/6/25, 10:33:30] Juan: Todo bien, hablemos del proyecto
[17/6/25, 9:00:00] Carlos: Buenos días, ¿listo para la reunión?
[17/6/25, 9:01:00] Juan: Sí, conectándonos ahora
"""

CHAT_ANDROID = """\
16/6/25, 10:32 - Juan: Hola
16/6/25, 10:33 - Carlos: Hola también
17/6/25, 9:00 - Carlos: ¿Nos vemos hoy?
"""

def test_parsear_whatsapp_ios():
    mensajes = parsear_whatsapp(CHAT_IOS)
    assert len(mensajes) >= 4
    assert mensajes[0].remitente == "Juan"
    assert mensajes[1].remitente == "Carlos"

def test_parsear_whatsapp_android():
    mensajes = parsear_whatsapp(CHAT_ANDROID)
    assert len(mensajes) >= 3

def test_parsear_fecha_normalizada():
    mensajes = parsear_whatsapp(CHAT_IOS)
    assert mensajes[0].fecha == "2025-06-16"

def test_parsear_omite_mensajes_sistema():
    chat = "[16/6/25, 10:00] Sistema: Los mensajes y las llamadas están cifrados\n"
    chat += "[16/6/25, 10:01] Carlos: Hola\n"
    mensajes = parsear_whatsapp(chat)
    assert len(mensajes) == 1
    assert mensajes[0].remitente == "Carlos"

def test_parsear_omite_media():
    chat = "[16/6/25, 10:00] Carlos: image omitted\n"
    chat += "[16/6/25, 10:01] Carlos: Mensaje real\n"
    mensajes = parsear_whatsapp(chat)
    assert len(mensajes) == 1


# ── agrupar_en_dia ────────────────────────────────────────────────────────────

def test_agrupar_filtra_por_remitente_externo():
    mensajes = parsear_whatsapp(CHAT_IOS)
    grupos = agrupar_en_dia(mensajes, "Carlos")
    assert all(g["fecha"] in ["2025-06-16", "2025-06-17"] for g in grupos)

def test_agrupar_un_grupo_por_dia():
    mensajes = parsear_whatsapp(CHAT_IOS)
    grupos = agrupar_en_dia(mensajes, "Carlos")
    fechas = [g["fecha"] for g in grupos]
    assert len(fechas) == len(set(fechas))  # sin duplicados de fecha

def test_agrupar_resumen_indica_mensajes_extra():
    chat = "\n".join(
        f"[16/6/25, 10:{i:02d}:00] Carlos: Mensaje {i}" for i in range(5)
    )
    mensajes = parsear_whatsapp(chat)
    grupos = agrupar_en_dia(mensajes, "Carlos")
    assert "+4 mensajes" in grupos[0]["resumen"]


# ── parsear_texto ─────────────────────────────────────────────────────────────

def test_parsear_texto_separa_parrafos():
    texto = "Primer párrafo con contenido.\n\nSegundo párrafo distinto.\n\nTercero."
    mensajes = parsear_texto(texto, "2026-06-26")
    assert len(mensajes) == 3

def test_parsear_texto_omite_parrafos_cortos():
    texto = "ok\n\nEste sí tiene contenido suficiente."
    mensajes = parsear_texto(texto, "2026-06-26")
    assert len(mensajes) == 1

def test_parsear_texto_fecha_asignada():
    mensajes = parsear_texto("Texto de prueba con contenido.", "2026-01-15")
    assert mensajes[0].fecha == "2026-01-15"


# ── parsear_csv ───────────────────────────────────────────────────────────────

def test_parsear_csv_basico():
    csv = "fecha,resumen\n2026-06-01,Hablamos del proyecto\n2026-06-05,Cerramos el contrato"
    mensajes = parsear_csv(csv)
    assert len(mensajes) == 2
    assert mensajes[0].fecha == "2026-06-01"
    assert mensajes[0].texto == "Hablamos del proyecto"

def test_parsear_csv_sin_encabezado():
    csv = "2026-06-01,Nota directa\n2026-06-02,Segunda nota"
    mensajes = parsear_csv(csv)
    assert len(mensajes) == 2

def test_parsear_csv_omite_filas_vacias():
    csv = "fecha,resumen\n\n2026-06-01,Válida\n,sin fecha"
    mensajes = parsear_csv(csv)
    assert len(mensajes) == 1
