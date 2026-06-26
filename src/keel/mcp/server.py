"""Servidor MCP de keel-core.

Expone el motor de extensión cognitiva como herramientas MCP.
Diseñado para ser consumido por Claude Code u otros clientes MCP.

Herramientas:
  keel_get_context   — contexto semántico para un mensaje (sin llamar al LLM)
  keel_respond       — sugerencia completa vía Ollama
  keel_remember      — agrega nota/promesa al grafo de relaciones
  keel_list_personas — lista personas registradas
  keel_get_persona   — perfil completo de una persona

Recursos:
  keel://perfil      — PerfilUsuario del dueño
  keel://personas    — resumen de todas las personas

Inicio:
  keel mcp           (stdio, para Claude Code y clientes estándar)
"""

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "keel-core",
    instructions=(
        "Motor de extensión cognitiva personal de Juan Diego / Imagine Robots. "
        "Usa keel_get_context para recuperar contexto relevante sobre una persona "
        "antes de redactar una respuesta. Usa keel_remember para registrar "
        "conversaciones o promesas importantes."
    ),
)


# ─── Herramientas ────────────────────────────────────────────────────────────


@mcp.tool()
def keel_get_context(mensaje: str, remitente: str) -> str:
    """Recupera el contexto relevante para responder a un mensaje.

    Devuelve el perfil del usuario, el historial semántico con el remitente
    y las promesas pendientes — listo para usarse como contexto en un prompt.
    No llama a ningún LLM; la generación queda en manos del cliente.

    Args:
        mensaje: El mensaje recibido al que hay que responder.
        remitente: Nombre de quien envió el mensaje.
    """
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import construir_prompt
    from keel.engine.presencia import analizar_tono
    from keel.embedder.fastembed import get_embedder

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init` para crearlo."

    persona = cargar_persona(remitente)
    tono = analizar_tono(mensaje)

    try:
        embedder = get_embedder()
    except Exception:
        embedder = None

    prompt = construir_prompt(perfil, persona, mensaje, tono.resumen, embedder)
    return prompt


@mcp.tool()
def keel_respond(mensaje: str, remitente: str, modelo: str = "qwen2.5-coder:7b") -> str:
    """Genera una sugerencia de respuesta usando el LLM local (Ollama).

    Usa el perfil del usuario, el historial con el remitente y la capa
    Présence para calibrar el tono. Devuelve el texto sugerido listo para editar.

    Args:
        mensaje: El mensaje recibido al que hay que responder.
        remitente: Nombre de quien envió el mensaje.
        modelo: Modelo Ollama a usar (default: qwen2.5-coder:7b).
    """
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import generar_sugerencia
    from keel.llm.ollama import OllamaLLM
    from keel.embedder.fastembed import get_embedder

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init` para crearlo."

    persona = cargar_persona(remitente)
    llm = OllamaLLM(modelo=modelo)

    if not llm.disponible():
        return "ERROR: Ollama no disponible. Ejecuta `ollama serve`."

    try:
        embedder = get_embedder()
    except Exception:
        embedder = None

    return generar_sugerencia(perfil, persona, mensaje, llm, embedder)


@mcp.tool()
def keel_remember(nota: str, persona: str = "", temas: str = "") -> str:
    """Agrega una nota o promesa al grafo de relaciones.

    Si la nota empieza con 'prometí', se registra como PromesaPendiente.
    Si se indica una persona, se asocia a su historial.

    Args:
        nota: Texto a recordar (ej: 'Prometí enviar el informe el viernes').
        persona: Nombre de la persona relacionada (opcional).
        temas: Temas separados por coma (ej: 'proyecto,deadline').
    """
    from keel.storage.local import cargar_persona, guardar_persona
    from keel.storage.vectorial import indexar_conversacion
    from keel.embedder.fastembed import get_embedder
    from keel.models.persona import ConversacionResumen, PromesaPendiente
    from datetime import date

    hoy = date.today().isoformat()
    temas_lista = [t.strip() for t in temas.split(",") if t.strip()]
    guardado_en = []

    if persona:
        p = cargar_persona(persona)
        if nota.lower().startswith("prometi") or nota.lower().startswith("prometí"):
            p.promesas_pendientes.append(PromesaPendiente(descripcion=nota, fecha_compromiso=hoy))
            guardado_en.append(f"promesa en perfil de {persona}")
        else:
            p.historial_conversaciones.append(
                ConversacionResumen(fecha=hoy, resumen=nota, temas=temas_lista)
            )
            guardado_en.append(f"historial de {persona}")
        guardar_persona(p)

    try:
        embedder = get_embedder()
        indexar_conversacion(persona or "_global", hoy, nota, temas_lista, embedder)
        guardado_en.append("LanceDB")
    except Exception:
        pass

    if not guardado_en:
        return "Nota recibida pero no indexada (sin persona y sin embedder disponible)."

    return f"✓ Guardado en: {', '.join(guardado_en)}."


@mcp.tool()
def keel_list_personas() -> str:
    """Lista todas las personas registradas en el grafo de relaciones.

    Devuelve nombre, rol, tono relacional, cantidad de conversaciones
    y promesas pendientes de cada persona.
    """
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona

    personas_dir = keel_dir() / "personas"
    if not personas_dir.exists():
        return "No hay personas registradas. Usa `keel persona add Nombre`."

    archivos = sorted(personas_dir.glob("*.json"))
    if not archivos:
        return "No hay personas registradas."

    filas = []
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        filas.append(
            f"- {p.nombre} | {p.rol or 'sin rol'} | tono: {p.tono_relacional} "
            f"| {len(p.historial_conversaciones)} conversaciones "
            f"| {len(p.promesas_pendientes)} promesas pendientes"
        )
    return "\n".join(filas)


@mcp.tool()
def keel_get_persona(nombre: str) -> str:
    """Devuelve el perfil completo de una persona en formato JSON.

    Incluye rol, historial de conversaciones, promesas pendientes
    y sensibilidades registradas.

    Args:
        nombre: Nombre de la persona (insensible a mayúsculas).
    """
    from keel.storage.local import cargar_persona
    p = cargar_persona(nombre)
    return p.model_dump_json(indent=2)


# ─── Prompts ─────────────────────────────────────────────────────────────────


@mcp.prompt()
def keel_responder(mensaje: str, remitente: str) -> str:
    """Template para redactar una respuesta con contexto de Keel.

    Recupera el contexto completo (perfil + historial semántico + promesas)
    y lo prepara como instrucción para que el LLM genere la respuesta.

    Args:
        mensaje: El mensaje recibido al que hay que responder.
        remitente: Nombre de quien envió el mensaje.
    """
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.respuesta import construir_prompt
    from keel.engine.presencia import analizar_tono
    from keel.embedder.fastembed import get_embedder

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init` para crearlo."

    persona = cargar_persona(remitente)
    tono = analizar_tono(mensaje)

    try:
        embedder = get_embedder()
    except Exception:
        embedder = None

    return construir_prompt(perfil, persona, mensaje, tono.resumen, embedder)


@mcp.prompt()
def keel_agenda_prompt() -> str:
    """Muestra todos los compromisos pendientes para revisión con el LLM.

    Útil para pedir a Claude que ayude a priorizar o redactar seguimientos.
    """
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from datetime import date

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    hoy = date.today().isoformat()

    lineas = [f"Compromisos pendientes al {hoy}:\n"]
    total = 0
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        for promesa in p.promesas_pendientes:
            vencida = promesa.fecha_compromiso and promesa.fecha_compromiso < hoy
            estado = "⚠ VENCIDA" if vencida else ""
            lineas.append(
                f"- {p.nombre}: {promesa.descripcion}"
                + (f" (límite: {promesa.fecha_compromiso} {estado})" if promesa.fecha_compromiso else "")
            )
            total += 1

    if total == 0:
        return "No hay compromisos pendientes registrados."

    lineas.append(f"\nTotal: {total} compromisos.")
    return "\n".join(lineas)


# ─── Recursos ────────────────────────────────────────────────────────────────


@mcp.resource("keel://perfil")
def resource_perfil() -> str:
    """Perfil del usuario: voz, valores, contexto vital."""
    from keel.storage.local import cargar_perfil
    try:
        return cargar_perfil().model_dump_json(indent=2)
    except FileNotFoundError:
        return json.dumps({"error": "Perfil no encontrado. Ejecuta: keel init"})


@mcp.resource("keel://personas")
def resource_personas() -> str:
    """Resumen de todas las personas en el grafo de relaciones."""
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona

    personas_dir = keel_dir() / "personas"
    if not personas_dir.exists():
        return json.dumps([])

    resultado = []
    for archivo in sorted(personas_dir.glob("*.json")):
        p = Persona.model_validate_json(archivo.read_text())
        resultado.append({
            "nombre": p.nombre,
            "rol": p.rol,
            "tono_relacional": p.tono_relacional,
            "ultima_interaccion": p.ultima_interaccion,
            "promesas_pendientes": len(p.promesas_pendientes),
        })
    return json.dumps(resultado, ensure_ascii=False, indent=2)
