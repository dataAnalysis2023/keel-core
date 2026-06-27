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
        "conversaciones o promesas importantes. "
        "Usa keel_buscar para encontrar conversaciones previas sobre un tema. "
        "Usa keel_reflexionar para obtener el estado relacional de la semana. "
        "Usa keel_preparar para un briefing completo antes de hablar con alguien. "
        "Usa keel_historial para ver el historial cronológico de una persona. "
        "Usa keel_stats para un panorama estadístico del grafo relacional. "
        "Usa keel_agenda_add para registrar una promesa con fecha explícita. "
        "Usa keel_sugerir para saber a quién contactar hoy por urgencia relacional. "
        "Usa keel_aprender para ver qué patrones sugiere el LLM sobre el perfil. "
        "Usa keel_pregunta para responder preguntas usando el historial como contexto. "
        "Usa keel_notas_add para capturar ideas o decisiones propias. "
        "Usa keel_notas_buscar para buscar en tus notas personales. "
        "Usa keel_notas_ver para listar las notas más recientes. "
        "Usa keel_alias_add para crear un atajo de nombre de persona. "
        "Usa keel_alias_list para ver todos los alias definidos. "
        "Usa keel_alias_borrar para eliminar un alias. "
        "Usa keel_sintetizar_persona para inferir la narrativa y tipo de relación de una persona desde su historial."
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


@mcp.tool()
def keel_buscar(texto: str, persona: str = "", top: int = 5, desde: str = "", hasta: str = "") -> str:
    """Busca en el historial de conversaciones por tema o texto.

    Usa búsqueda semántica si hay embedder disponible, keyword si no.
    Devuelve los resultados más relevantes con persona, fecha y resumen.

    Args:
        texto: Tema o texto a buscar en el historial.
        persona: Si se especifica, filtra por esa persona (opcional).
        top: Número máximo de resultados (default: 5).
        desde: Fecha inicio YYYY-MM-DD inclusive (opcional).
        hasta: Fecha fin YYYY-MM-DD inclusive (opcional).
    """
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.busqueda import buscar_global
    from keel.embedder.fastembed import get_embedder

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas_lista = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas_lista:
        return "No hay personas registradas con historial."

    try:
        embedder = get_embedder()
    except Exception:
        embedder = None

    resultados = buscar_global(
        texto,
        personas_lista,
        embedder,
        top=top,
        filtro_persona=persona or None,
        desde=desde or None,
        hasta=hasta or None,
    )

    if not resultados:
        filtros = []
        if desde:
            filtros.append(f"desde {desde}")
        if hasta:
            filtros.append(f"hasta {hasta}")
        sufijo = f" ({', '.join(filtros)})" if filtros else ""
        return f"Sin resultados para '{texto}'{sufijo}."

    modo = resultados[0].get("modo", "keyword")
    lineas = [f"Resultados para '{texto}' (modo {modo}):\n"]
    for r in resultados:
        temas = f" [{r['temas']}]" if r.get("temas") else ""
        lineas.append(f"- {r['persona']} | {r['fecha']}{temas}: {r['resumen']}")
    return "\n".join(lineas)


@mcp.tool()
def keel_reflexionar(dias_promesa: int = 7, dias_silencio: int = 14) -> str:
    """Genera un digest del estado relacional de la semana.

    Incluye compromisos próximos a vencer, personas sin contacto reciente
    y temas recurrentes. Devuelve Markdown listo para leer o copiar.

    Args:
        dias_promesa: Alerta si una promesa vence en <= N días (default: 7).
        dias_silencio: Alerta si no hubo contacto en >= N días (default: 14).
    """
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.reflexion import construir_digest, digest_a_markdown

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas_lista = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas_lista:
        return "No hay personas registradas."

    digest = construir_digest(
        personas_lista,
        dias_promesa=dias_promesa,
        dias_sin_contacto=dias_silencio,
    )
    return digest_a_markdown(digest)


@mcp.tool()
def keel_aprender() -> str:
    """Analiza el historial y sugiere actualizaciones al perfil del usuario.

    Detecta frases recurrentes, vocabulario propio, valores implícitos
    y temas frecuentes. Devuelve las sugerencias en texto — no las aplica.
    Para aplicarlas usa `keel perfil actualizar` en la terminal.
    """
    from keel.storage.local import cargar_perfil, keel_dir
    from keel.models.persona import Persona
    from keel.engine.aprendizaje import analizar_historial
    from keel.llm.ollama import OllamaLLM

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init`."

    llm = OllamaLLM()
    if not llm.disponible():
        return "ERROR: Ollama no disponible. Ejecuta `ollama serve`."

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []

    conversaciones: dict[str, list[str]] = {}
    for archivo in archivos:
        p = Persona.model_validate_json(archivo.read_text())
        resumenes = [c.resumen for c in p.historial_conversaciones if c.resumen]
        if len(resumenes) >= 2:
            conversaciones[p.nombre] = resumenes

    if not conversaciones:
        return "Sin historial suficiente para analizar (mínimo 2 conversaciones por persona)."

    sugerencias = analizar_historial(perfil, conversaciones, llm)

    lineas = [f"Análisis del perfil de {perfil.nombre}:\n"]
    if sugerencias.resumen:
        lineas.append(f"{sugerencias.resumen}\n")
    if sugerencias.frases_nuevas:
        lineas.append(f"Frases detectadas: {', '.join(sugerencias.frases_nuevas)}")
    if sugerencias.vocabulario_nuevo:
        lineas.append(f"Vocabulario: {', '.join(sugerencias.vocabulario_nuevo)}")
    if sugerencias.valores_detectados:
        lineas.append(f"Valores implícitos: {', '.join(sugerencias.valores_detectados)}")
    if sugerencias.temas_recurrentes:
        lineas.append(f"Temas recurrentes: {', '.join(sugerencias.temas_recurrentes)}")

    lineas.append("\nPara aplicar: `keel perfil actualizar`")
    return "\n".join(lineas)


@mcp.tool()
def keel_sugerir(top: int = 3) -> str:
    """Sugiere quién contactar hoy y por qué, ordenado por urgencia relacional.

    Prioriza: promesas vencidas > promesas próximas > días sin contacto.
    Útil para decidir a quién escribir al inicio del día o de la semana.

    Args:
        top: Número de contactos sugeridos (default: 3).
    """
    from keel.storage.local import keel_dir, cargar_config
    from keel.models.persona import Persona
    from keel.engine.sugerencias import sugerir_contactos, sugerencias_a_texto

    cfg = cargar_config()
    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas:
        return "No hay personas registradas."

    sugerencias = sugerir_contactos(
        personas, top=top,
        dias_silencio=cfg.dias_silencio,
        dias_promesa=cfg.dias_promesa,
    )
    return sugerencias_a_texto(sugerencias)


@mcp.tool()
def keel_preparar(persona: str, n_recientes: int = 5) -> str:
    """Genera un briefing pre-conversación sobre una persona.

    Recopila rol, sensibilidades, estado actual, promesas pendientes,
    conversaciones recientes y temas frecuentes. Incluye síntesis LLM
    si Ollama está disponible. Úsalo antes de hablar con alguien.

    Args:
        persona: Nombre de la persona con la que vas a hablar.
        n_recientes: Número de conversaciones recientes a incluir (default: 5).
    """
    from keel.storage.local import cargar_perfil, cargar_persona
    from keel.engine.preparar import briefing_a_markdown, construir_prompt_briefing

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init`."

    p = cargar_persona(persona)

    sintesis = ""
    from keel.llm.ollama import OllamaLLM
    llm = OllamaLLM()
    if llm.disponible():
        prompt = construir_prompt_briefing(p, perfil.nombre, n_recientes=n_recientes)
        sintesis = llm.generar(prompt)

    return briefing_a_markdown(p, sintesis, n_recientes=n_recientes)


@mcp.tool()
def keel_pregunta(pregunta: str, persona: str = "", top: int = 5) -> str:
    """Responde una pregunta usando el historial como contexto.

    Sin persona, busca en todos los historiales (modo global).
    Con persona, limita la búsqueda a esa persona.

    Args:
        pregunta: La pregunta a responder (ej: "¿qué acordamos sobre el proyecto X?").
        persona: Nombre de la persona (vacío = buscar en todas).
        top: Fragmentos de historial a usar como contexto (default: 5).
    """
    from keel.storage.local import cargar_perfil, cargar_persona, keel_dir
    from keel.models.persona import Persona
    from keel.engine.busqueda import buscar_global
    from keel.engine.pregunta import construir_prompt_pregunta, respuesta_sin_llm

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init`."

    if persona:
        p = cargar_persona(persona)
        personas = [p]
        persona_obj: Persona | None = p
        notas = []
    else:
        personas_dir = keel_dir() / "personas"
        archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
        personas = [Persona.model_validate_json(a.read_text()) for a in archivos]
        persona_obj = None
        from keel.storage.local import cargar_notas
        notas = cargar_notas()

    embedder = None
    try:
        from keel.embedder.fastembed import FastEmbedder
        embedder = FastEmbedder()
    except Exception:
        pass

    from keel.engine.busqueda import buscar_notas
    contexto = buscar_global(pregunta, personas, embedder=embedder, top=top)
    if notas:
        ctx_notas = buscar_notas(pregunta, notas, embedder=embedder, top=top)
        contexto = sorted(contexto + ctx_notas, key=lambda r: r.get("fecha", ""), reverse=True)[:top]

    from keel.llm.ollama import OllamaLLM
    llm = OllamaLLM()
    if llm.disponible():
        prompt = construir_prompt_pregunta(pregunta, persona_obj, perfil.nombre, contexto)
        return llm.generar(prompt)

    return respuesta_sin_llm(contexto, persona or None)


@mcp.tool()
def keel_notas_add(contenido: str, temas: str = "") -> str:
    """Agrega una nota personal al diario de keel.

    Úsalo para capturar ideas, decisiones, contexto o recordatorios propios
    que no están ligados a una persona específica. Las notas quedan indexadas
    y aparecen en keel_pregunta (modo global).

    Args:
        contenido: El texto de la nota.
        temas: Temas separados por coma (ej: "legal,proyecto") — opcional.
    """
    from keel.models.nota import Nota
    from keel.storage.local import agregar_nota

    lista_temas = [t.strip() for t in temas.split(",") if t.strip()] if temas else []
    nota = Nota(contenido=contenido, temas=lista_temas)
    agregar_nota(nota)

    try:
        from keel.embedder.fastembed import FastEmbedder
        from keel.storage.vectorial import indexar_conversacion
        embedder = FastEmbedder()
        indexar_conversacion("_notas", nota.fecha, nota.contenido, lista_temas, embedder)
    except Exception:
        pass

    temas_str = f" [{', '.join(lista_temas)}]" if lista_temas else ""
    return f"✓ Nota guardada [{nota.id}]{temas_str}: {contenido[:80]}"


@mcp.tool()
def keel_notas_buscar(texto: str, top: int = 5) -> str:
    """Busca en las notas personales por contenido o tema.

    Args:
        texto: Texto a buscar en el contenido y temas de las notas.
        top: Número máximo de resultados (default: 5).
    """
    from keel.storage.local import cargar_notas
    from keel.engine.busqueda import buscar_notas

    notas = cargar_notas()

    embedder = None
    try:
        from keel.embedder.fastembed import FastEmbedder
        embedder = FastEmbedder()
    except Exception:
        pass

    resultados = buscar_notas(texto, notas, embedder=embedder, top=top)

    if not resultados:
        return f"Sin notas que coincidan con '{texto}'."

    lineas = [f"Notas relevantes para '{texto}':\n"]
    for r in resultados:
        temas = r.get("temas", "")
        if isinstance(temas, list):
            temas = ", ".join(temas)
        temas_str = f" [{temas}]" if temas else ""
        lineas.append(f"- [{r['fecha']}]{temas_str}: {r['resumen']}")
    return "\n".join(lineas)


@mcp.tool()
def keel_notas_ver(top: int = 10) -> str:
    """Devuelve las notas personales más recientes.

    Args:
        top: Número de notas a mostrar (default: 10).
    """
    from keel.storage.local import cargar_notas

    notas = sorted(cargar_notas(), key=lambda n: n.fecha, reverse=True)[:top]

    if not notas:
        return "No hay notas registradas."

    lineas = [f"Últimas {len(notas)} nota(s):\n"]
    for nota in notas:
        temas_str = f" [{', '.join(nota.temas)}]" if nota.temas else ""
        lineas.append(f"- [{nota.fecha}] ({nota.id}){temas_str}: {nota.contenido}")
    return "\n".join(lineas)


@mcp.tool()
def keel_historial(persona: str, desde: str = "", hasta: str = "", top: int = 0) -> str:
    """Devuelve el historial cronológico de conversaciones con una persona.

    Ordena de más antiguo a más reciente. Acepta filtros opcionales por rango
    de fechas y límite de entradas más recientes.

    Args:
        persona: Nombre de la persona.
        desde: Fecha de inicio YYYY-MM-DD (inclusive, opcional).
        hasta: Fecha de fin YYYY-MM-DD (inclusive, opcional).
        top: Si > 0, devuelve solo los N más recientes (opcional).
    """
    from keel.storage.local import cargar_persona

    p = cargar_persona(persona)

    if not p.historial_conversaciones:
        return f"No hay historial registrado para '{persona}'."

    entradas = sorted(p.historial_conversaciones, key=lambda c: c.fecha)

    if desde:
        entradas = [c for c in entradas if c.fecha >= desde]
    if hasta:
        entradas = [c for c in entradas if c.fecha <= hasta]
    if top > 0:
        entradas = entradas[-top:]

    if not entradas:
        return f"Sin conversaciones en ese rango para '{persona}'."

    lineas = [f"Historial de {persona} — {len(entradas)} entrada(s):\n"]
    for c in entradas:
        temas = f" [{', '.join(c.temas)}]" if c.temas else ""
        lineas.append(f"- {c.fecha}{temas}: {c.resumen}")

    return "\n".join(lineas)


@mcp.tool()
def keel_agenda_add(persona: str, descripcion: str, fecha: str = "") -> str:
    """Agrega una promesa pendiente a la agenda de una persona.

    Más explícito que keel_remember: no requiere el prefijo 'prometí'
    y acepta fecha límite directamente en formato YYYY-MM-DD.

    Args:
        persona: Nombre de la persona con quien se hizo el compromiso.
        descripcion: Descripción del compromiso (qué prometiste hacer).
        fecha: Fecha límite YYYY-MM-DD (opcional).
    """
    from keel.storage.local import cargar_persona, guardar_persona
    from keel.models.persona import PromesaPendiente
    from datetime import date as _date

    if fecha:
        try:
            _date.fromisoformat(fecha)
        except ValueError:
            return f"ERROR: Fecha inválida '{fecha}'. Usa formato YYYY-MM-DD."

    p = cargar_persona(persona)
    p.promesas_pendientes.append(PromesaPendiente(descripcion=descripcion, fecha_compromiso=fecha or None))
    guardar_persona(p)

    fecha_str = f" (hasta {fecha})" if fecha else ""
    return f"✓ Promesa agregada a {persona}: '{descripcion}'{fecha_str}."


@mcp.tool()
def keel_stats() -> str:
    """Devuelve estadísticas del grafo relacional en texto.

    Incluye: totales globales, personas más activas, temas frecuentes,
    actividad mensual y promesas vencidas. Útil para revisar el estado
    de la red de relaciones de un vistazo.
    """
    from keel.storage.local import keel_dir
    from keel.models.persona import Persona
    from keel.engine.stats import calcular_stats

    personas_dir = keel_dir() / "personas"
    archivos = sorted(personas_dir.glob("*.json")) if personas_dir.exists() else []
    personas = [Persona.model_validate_json(a.read_text()) for a in archivos]

    if not personas:
        return "No hay personas registradas."

    s = calcular_stats(personas)

    lineas = [
        f"Personas: {s['total_personas']} | Conversaciones: {s['total_conversaciones']} | Promesas pendientes: {s['total_promesas_pendientes']}\n",
    ]

    if s["personas_activas"]:
        lineas.append("Personas más activas:")
        for d in s["personas_activas"]:
            lineas.append(f"  {d['nombre']}: {d['conversaciones']} conversaciones (última: {d['ultima']})")

    if s["temas_frecuentes"]:
        temas = ", ".join(f"{d['tema']} ×{d['menciones']}" for d in s["temas_frecuentes"][:6])
        lineas.append(f"\nTemas frecuentes: {temas}")

    if s["promesas_vencidas"]:
        lineas.append(f"\n⚠ Promesas vencidas ({len(s['promesas_vencidas'])}):")
        for d in s["promesas_vencidas"]:
            lineas.append(f"  {d['persona']}: {d['descripcion']} (hace {d['dias_vencida']}d)")

    if s["sin_historial"]:
        lineas.append(f"\nSin historial: {', '.join(s['sin_historial'])}")

    return "\n".join(lineas)


@mcp.tool()
def keel_sintetizar_persona(persona: str) -> str:
    """Infiere narrativa, tipo de relación y contexto situacional de una persona usando el LLM.

    Lee el historial de conversaciones y deduce el carácter real de la relación
    sin requerir input explícito del usuario. Actualiza los campos narrativa,
    tipo_relacion y contexto_situacional en el perfil de la persona.

    Args:
        persona: Nombre de la persona a sintetizar.
    """
    from keel.storage.local import cargar_perfil, cargar_persona, guardar_persona
    from keel.engine.sintesis import sintetizar_persona as _sintetizar, aplicar_sintesis
    from keel.llm.ollama import OllamaLLM

    try:
        perfil = cargar_perfil()
    except FileNotFoundError:
        return "ERROR: Perfil no encontrado. Ejecuta `keel init`."

    p = cargar_persona(persona)
    if not p.historial_conversaciones:
        return f"'{persona}' no tiene historial suficiente para sintetizar."

    llm = OllamaLLM()
    if not llm.disponible():
        return "ERROR: Ollama no disponible. Ejecuta `ollama serve`."

    sintesis = _sintetizar(p, perfil, llm)
    aplicar_sintesis(p, sintesis)
    guardar_persona(p)

    lineas = [f"Síntesis de {persona} [{sintesis.tipo_relacion}]:\n"]
    lineas.append(sintesis.narrativa)
    if sintesis.contexto_situacional:
        lineas.append(f"\nContexto: {sintesis.contexto_situacional}")
    return "\n".join(lineas)


@mcp.tool()
def keel_alias_add(alias: str, persona: str) -> str:
    """Define un alias para el nombre de una persona.

    Después de crearlo, cualquier comando que acepte un nombre de persona
    también acepta el alias (ej: keel_pregunta con persona='jc' si 'jc' → 'Juan Carlos').

    Args:
        alias: El atajo a crear (ej: 'jc', 'ceo', 'el_cliente').
        persona: El nombre real de la persona en keel (ej: 'Juan Carlos').
    """
    from keel.storage.local import cargar_aliases, guardar_aliases

    aliases = cargar_aliases()
    existia = alias.lower() in aliases
    aliases[alias.lower()] = persona
    guardar_aliases(aliases)

    accion = "actualizado" if existia else "creado"
    return f"✓ Alias {accion}: '{alias}' → '{persona}'."


@mcp.tool()
def keel_alias_list() -> str:
    """Lista todos los alias de nombres de personas definidos."""
    from keel.storage.local import cargar_aliases

    aliases = cargar_aliases()
    if not aliases:
        return "No hay alias definidos. Usa keel_alias_add para crear uno."

    lineas = [f"Aliases definidos ({len(aliases)}):\n"]
    for alias, persona in sorted(aliases.items()):
        lineas.append(f"  {alias} → {persona}")
    return "\n".join(lineas)


@mcp.tool()
def keel_alias_borrar(alias: str) -> str:
    """Elimina un alias de nombre de persona.

    Args:
        alias: El atajo a eliminar.
    """
    from keel.storage.local import cargar_aliases, guardar_aliases

    aliases = cargar_aliases()
    alias_lower = alias.lower()

    if alias_lower not in aliases:
        return f"ERROR: Alias '{alias}' no encontrado."

    persona = aliases.pop(alias_lower)
    guardar_aliases(aliases)
    return f"✓ Alias '{alias}' → '{persona}' eliminado."


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
