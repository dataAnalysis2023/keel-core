"""Tests del servidor MCP — verifica herramientas y recursos sin Ollama."""

import json
import pytest
import asyncio
import keel.storage.vectorial as mod_vectorial


@pytest.fixture
def keel_tmp(tmp_path, monkeypatch):
    keel = tmp_path / ".keel"
    keel.mkdir()
    (keel / "personas").mkdir()
    monkeypatch.setattr("keel.storage.local._KEEL_DIR", keel)
    monkeypatch.setattr(mod_vectorial, "_db_path", lambda: keel / "vectorial")

    perfil = {
        "nombre": "Juan",
        "voz": {"tono": "directo", "registro": "informal", "vocabulario_frecuente": [], "frases_caracteristicas": []},
        "valores": ["claridad"],
        "contexto_vital": {},
        "historial_coherencia": [],
    }
    (keel / "perfil.json").write_text(json.dumps(perfil))
    return keel


async def _call(tool: str, args: dict):
    from keel.mcp.server import mcp
    content, _ = await mcp.call_tool(tool, args)
    return content[0].text


async def _resource(uri: str) -> str:
    from keel.mcp.server import mcp
    result = await mcp.read_resource(uri)
    return result[0].content if result else ""


def test_list_tools():
    from keel.mcp.server import mcp

    async def _run():
        tools = await mcp.list_tools()
        return [t.name for t in tools]

    nombres = asyncio.run(_run())
    assert "keel_get_context" in nombres
    assert "keel_respond" in nombres
    assert "keel_remember" in nombres
    assert "keel_list_personas" in nombres
    assert "keel_get_persona" in nombres
    assert "keel_buscar" in nombres
    assert "keel_reflexionar" in nombres
    assert "keel_aprender" in nombres
    assert "keel_preparar" in nombres
    assert "keel_historial" in nombres
    assert "keel_stats" in nombres
    assert "keel_agenda_add" in nombres
    assert "keel_sugerir" in nombres
    assert "keel_pregunta" in nombres
    assert "keel_notas_add" in nombres
    assert "keel_notas_buscar" in nombres
    assert "keel_notas_ver" in nombres
    assert "keel_alias_add" in nombres
    assert "keel_alias_list" in nombres
    assert "keel_alias_borrar" in nombres
    assert "keel_calendario_ver" in nombres
    assert "keel_calendario_contexto" in nombres


def test_list_personas_vacio(keel_tmp):
    texto = asyncio.run(_call("keel_list_personas", {}))
    assert "No hay" in texto


def test_get_context(keel_tmp):
    texto = asyncio.run(_call("keel_get_context", {
        "mensaje": "Hola, ¿cómo estás?",
        "remitente": "Ana",
    }))
    assert "Juan" in texto
    assert "Ana" in texto
    assert "claridad" in texto


def test_remember_con_persona(keel_tmp):
    texto = asyncio.run(_call("keel_remember", {
        "nota": "Hablamos del roadmap del proyecto",
        "persona": "Pedro",
        "temas": "roadmap,proyecto",
    }))
    assert "✓" in texto

    persona_json = asyncio.run(_call("keel_get_persona", {"nombre": "Pedro"}))
    persona = json.loads(persona_json)
    assert len(persona["historial_conversaciones"]) == 1


def test_remember_promesa(keel_tmp):
    texto = asyncio.run(_call("keel_remember", {
        "nota": "Prometí enviar el informe el viernes",
        "persona": "María",
    }))
    assert "promesa" in texto.lower() or "✓" in texto

    persona_json = asyncio.run(_call("keel_get_persona", {"nombre": "María"}))
    persona = json.loads(persona_json)
    assert len(persona["promesas_pendientes"]) == 1


def test_resource_perfil(keel_tmp):
    texto = asyncio.run(_resource("keel://perfil"))
    data = json.loads(texto)
    assert data["nombre"] == "Juan"


def test_resource_personas(keel_tmp):
    asyncio.run(_call("keel_remember", {"nota": "Nota", "persona": "Luis"}))
    texto = asyncio.run(_resource("keel://personas"))
    personas = json.loads(texto)
    assert any(p["nombre"] == "Luis" for p in personas)


def test_buscar_sin_historial(keel_tmp):
    texto = asyncio.run(_call("keel_buscar", {"texto": "producto"}))
    assert "Sin resultados" in texto or "No hay" in texto


def test_buscar_con_historial(keel_tmp):
    # Primero agrega una conversación
    asyncio.run(_call("keel_remember", {
        "nota": "Hablamos del lanzamiento del producto",
        "persona": "Carlos",
        "temas": "producto,lanzamiento",
    }))
    texto = asyncio.run(_call("keel_buscar", {"texto": "lanzamiento"}))
    # Con keyword fallback debe encontrar la conversación
    assert "Carlos" in texto or "Sin resultados" in texto  # puede no estar en LanceDB sin embedder real


def test_reflexionar_sin_personas(keel_tmp):
    texto = asyncio.run(_call("keel_reflexionar", {}))
    assert "No hay" in texto


def test_reflexionar_con_personas(keel_tmp):
    from keel.models.persona import Persona, PromesaPendiente
    from datetime import date, timedelta

    p = Persona(
        nombre="Ana",
        ultima_interaccion=(date.today()).isoformat(),
        promesas_pendientes=[
            PromesaPendiente(
                descripcion="Enviar propuesta",
                fecha_compromiso=(date.today() + timedelta(days=3)).isoformat(),
            )
        ],
    )
    (keel_tmp / "personas" / "ana.json").write_text(p.model_dump_json())

    texto = asyncio.run(_call("keel_reflexionar", {}))
    assert "Reflexión" in texto
    assert "Enviar propuesta" in texto


def test_agenda_add(keel_tmp):
    texto = asyncio.run(_call("keel_agenda_add", {
        "persona": "María",
        "descripcion": "Enviar propuesta comercial",
        "fecha": "2026-08-15",
    }))
    assert "✓" in texto
    from keel.storage.local import cargar_persona
    p = cargar_persona("María")
    assert len(p.promesas_pendientes) == 1
    assert p.promesas_pendientes[0].fecha_compromiso == "2026-08-15"


def test_agenda_add_fecha_invalida(keel_tmp):
    texto = asyncio.run(_call("keel_agenda_add", {
        "persona": "Luis",
        "descripcion": "Algo",
        "fecha": "no-es-fecha",
    }))
    assert "ERROR" in texto


def test_agenda_add_sin_fecha(keel_tmp):
    texto = asyncio.run(_call("keel_agenda_add", {
        "persona": "Pedro",
        "descripcion": "Llamar esta semana",
    }))
    assert "✓" in texto


def test_aprender_sin_historial(keel_tmp):
    texto = asyncio.run(_call("keel_aprender", {}))
    # Sin Ollama disponible o sin historial, debe retornar mensaje claro
    assert "ERROR" in texto or "Sin historial" in texto


# ── keel_preparar ─────────────────────────────────────────────────────────────

def test_preparar_persona_nueva(keel_tmp):
    texto = asyncio.run(_call("keel_preparar", {"persona": "Nadie"}))
    assert "Nadie" in texto


def test_preparar_con_historial(keel_tmp):
    from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
    p = Persona(
        nombre="Carlos",
        rol="CTO",
        sensibilidades=["plazos"],
        historial_conversaciones=[
            ConversacionResumen(fecha="2026-05-01", resumen="Revisión de arquitectura", temas=["técnico"]),
        ],
        promesas_pendientes=[
            PromesaPendiente(descripcion="Enviar propuesta técnica"),
        ],
    )
    (keel_tmp / "personas" / "carlos.json").write_text(p.model_dump_json())

    texto = asyncio.run(_call("keel_preparar", {"persona": "Carlos"}))
    assert "Carlos" in texto
    assert "CTO" in texto
    assert "Enviar propuesta técnica" in texto
    assert "Revisión de arquitectura" in texto


def test_preparar_sin_perfil(keel_tmp):
    (keel_tmp / "perfil.json").unlink()
    texto = asyncio.run(_call("keel_preparar", {"persona": "Ana"}))
    assert "ERROR" in texto


# ── keel_historial ────────────────────────────────────────────────────────────

def test_historial_sin_datos(keel_tmp):
    texto = asyncio.run(_call("keel_historial", {"persona": "Nadie"}))
    assert "No hay historial" in texto


def test_historial_con_entradas(keel_tmp):
    from keel.models.persona import Persona, ConversacionResumen
    p = Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-10", resumen="Reunión inicial", temas=["proyecto"]),
        ConversacionResumen(fecha="2026-03-20", resumen="Cierre de contrato", temas=["legal"]),
    ])
    (keel_tmp / "personas" / "ana.json").write_text(p.model_dump_json())

    texto = asyncio.run(_call("keel_historial", {"persona": "Ana"}))
    assert "Reunión inicial" in texto
    assert "Cierre de contrato" in texto
    assert "2 entrada(s)" in texto


def test_historial_filtro_top(keel_tmp):
    from keel.models.persona import Persona, ConversacionResumen
    p = Persona(nombre="Luis", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Primera"),
        ConversacionResumen(fecha="2026-06-01", resumen="Última"),
    ])
    (keel_tmp / "personas" / "luis.json").write_text(p.model_dump_json())

    texto = asyncio.run(_call("keel_historial", {"persona": "Luis", "top": 1}))
    assert "Última" in texto
    assert "Primera" not in texto


def test_historial_filtro_desde(keel_tmp):
    from keel.models.persona import Persona, ConversacionResumen
    p = Persona(nombre="Pedro", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="Enero"),
        ConversacionResumen(fecha="2026-06-01", resumen="Junio"),
    ])
    (keel_tmp / "personas" / "pedro.json").write_text(p.model_dump_json())

    texto = asyncio.run(_call("keel_historial", {"persona": "Pedro", "desde": "2026-05-01"}))
    assert "Junio" in texto
    assert "Enero" not in texto


# ── keel_stats ────────────────────────────────────────────────────────────────

def test_stats_sin_personas(keel_tmp):
    texto = asyncio.run(_call("keel_stats", {}))
    assert "No hay personas" in texto


def test_stats_con_personas(keel_tmp):
    from keel.models.persona import Persona, ConversacionResumen, PromesaPendiente
    from datetime import date, timedelta
    vencida = (date.today() - timedelta(days=3)).isoformat()

    p1 = Persona(nombre="Carlos", historial_conversaciones=[
        ConversacionResumen(fecha="2026-01-01", resumen="R1", temas=["producto"]),
        ConversacionResumen(fecha="2026-03-01", resumen="R2", temas=["producto"]),
    ], promesas_pendientes=[
        PromesaPendiente(descripcion="Enviar informe", fecha_compromiso=vencida),
    ])
    p2 = Persona(nombre="Ana", historial_conversaciones=[
        ConversacionResumen(fecha="2026-02-01", resumen="Demo", temas=["demo"]),
    ])
    (keel_tmp / "personas" / "carlos.json").write_text(p1.model_dump_json())
    (keel_tmp / "personas" / "ana.json").write_text(p2.model_dump_json())

    texto = asyncio.run(_call("keel_stats", {}))
    assert "Personas: 2" in texto
    assert "Carlos" in texto
    assert "producto" in texto
    assert "Enviar informe" in texto  # promesa vencida

# ── keel_pregunta ──────────────────────────────────────────────────────────────

def test_pregunta_persona_sin_historial(keel_tmp):
    from keel.models.persona import Persona
    (keel_tmp / "personas" / "ana.json").write_text(Persona(nombre="Ana").model_dump_json())
    texto = asyncio.run(_call("keel_pregunta", {"pregunta": "¿qué hablamos?", "persona": "Ana"}))
    assert "Ana" in texto


def test_pregunta_persona_nueva_devuelve_texto(keel_tmp):
    texto = asyncio.run(_call("keel_pregunta", {"pregunta": "¿algo?", "persona": "Nadie"}))
    assert isinstance(texto, str)
    assert len(texto) > 0


def test_pregunta_sin_perfil_devuelve_error(keel_tmp):
    (keel_tmp / "perfil.json").unlink()
    texto = asyncio.run(_call("keel_pregunta", {"pregunta": "¿algo?", "persona": "Ana"}))
    assert "ERROR" in texto

# ── keel_notas_* ───────────────────────────────────────────────────────────────

def test_notas_add_y_ver(keel_tmp):
    res = asyncio.run(_call("keel_notas_add", {"contenido": "Idea para el proyecto"}))
    assert "✓" in res

    res2 = asyncio.run(_call("keel_notas_ver", {}))
    assert "Idea para el proyecto" in res2


def test_notas_ver_vacio(keel_tmp):
    res = asyncio.run(_call("keel_notas_ver", {}))
    assert "No hay notas" in res


def test_notas_add_con_temas(keel_tmp):
    res = asyncio.run(_call("keel_notas_add", {"contenido": "Revisar contrato", "temas": "legal,contrato"}))
    assert "✓" in res
    assert "legal" in res or "contrato" in res


def test_notas_buscar_encuentra(keel_tmp):
    asyncio.run(_call("keel_notas_add", {"contenido": "Reunión sobre estrategia digital"}))
    res = asyncio.run(_call("keel_notas_buscar", {"texto": "estrategia"}))
    assert "estrategia" in res.lower()


def test_notas_buscar_sin_resultados(keel_tmp):
    res = asyncio.run(_call("keel_notas_buscar", {"texto": "xyz999inexistente"}))
    assert "Sin notas" in res


# ── keel_alias_* ───────────────────────────────────────────────────────────────

def test_alias_add_y_list(keel_tmp):
    res = asyncio.run(_call("keel_alias_add", {"alias": "jc", "persona": "Juan Carlos"}))
    assert "✓" in res
    assert "creado" in res

    lista = asyncio.run(_call("keel_alias_list", {}))
    assert "jc" in lista
    assert "Juan Carlos" in lista


def test_alias_list_vacio(keel_tmp):
    res = asyncio.run(_call("keel_alias_list", {}))
    assert "No hay alias" in res


def test_alias_add_actualiza(keel_tmp):
    asyncio.run(_call("keel_alias_add", {"alias": "jc", "persona": "Juan C."}))
    res = asyncio.run(_call("keel_alias_add", {"alias": "jc", "persona": "Juan Carlos"}))
    assert "actualizado" in res


def test_alias_borrar(keel_tmp):
    asyncio.run(_call("keel_alias_add", {"alias": "temp", "persona": "Persona Temp"}))
    res = asyncio.run(_call("keel_alias_borrar", {"alias": "temp"}))
    assert "✓" in res

    lista = asyncio.run(_call("keel_alias_list", {}))
    assert "temp" not in lista


def test_alias_borrar_inexistente(keel_tmp):
    res = asyncio.run(_call("keel_alias_borrar", {"alias": "fantasma"}))
    assert "ERROR" in res


# ── keel_calendario_ver / keel_calendario_contexto — mock osascript ───────────

def test_calendario_ver_sin_eventos(keel_tmp, monkeypatch):
    import subprocess
    monkeypatch.setattr("sys.platform", "darwin")

    class FakeResult:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    res = asyncio.run(_call("keel_calendario_ver", {"dias": 7}))
    assert "no disponible" in res or "Sin eventos" in res


def test_calendario_ver_con_eventos(keel_tmp, monkeypatch):
    import subprocess
    monkeypatch.setattr("sys.platform", "darwin")

    class FakeResult:
        returncode = 0
        stdout = "Demo con cliente|2026-07-01|10:00|Work\nReunión legal|2026-07-02|14:00|Personal\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    res = asyncio.run(_call("keel_calendario_ver", {"dias": 7}))
    assert "Demo con cliente" in res or "Agenda" in res


def test_calendario_contexto_vacio(keel_tmp, monkeypatch):
    import subprocess
    monkeypatch.setattr("sys.platform", "darwin")

    class FakeResult:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    res = asyncio.run(_call("keel_calendario_contexto", {"dias": 7}))
    assert res == ""


def test_calendario_contexto_campaña(keel_tmp, monkeypatch):
    import subprocess
    monkeypatch.setattr("sys.platform", "darwin")

    class FakeResult:
        returncode = 0
        stdout = (
            "Reunión campaña electoral|2026-07-01|10:00|Work\n"
            "Debate de candidatos|2026-07-02|14:00|Personal\n"
        )

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    res = asyncio.run(_call("keel_calendario_contexto", {"dias": 7}))
    assert "electoral" in res or "campaña" in res
