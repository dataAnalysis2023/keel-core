---
proyecto: keel-core
tipo: roadmap
estado: activo
---

# ROADMAP — keel-core

> Documento de trazabilidad. El detalle cronológico de cada sesión vive en `ESTADO.md`.

## Hito 1 — Motor mínimo en CLI (completado 2026-06-26)

CLI funcional end-to-end: mensaje + remitente → sugerencia de respuesta vía Ollama.

- [x] Estructura del repositorio (src-layout, pyproject.toml)
- [x] Modelos Pydantic: PerfilUsuario, Persona
- [x] Abstracción LLMBase + implementación OllamaLLM
- [x] Capa Présence (análisis heurístico de tono)
- [x] Motor de respuesta — construye prompt, llama LLM (Módulo 3)
- [x] Storage local (carga JSON desde ~/.keel/)
- [x] CLI: `keel respond`, `keel init`, `keel status`
- [x] Tests unitarios de modelos y motor
- [x] Instalación `pip install -e .` verificada end-to-end
- [x] Prueba real con Ollama corriendo
- [x] `keel persona add/list/show`
- [x] Módulo 4 básico: guardar conversación en historial tras `keel respond`
- [x] git init + primer commit

## Hito 2 — Contexto vectorial (completado 2026-06-26)

- [x] LanceDB para almacenamiento vectorial local (~/.keel/vectorial/)
- [x] FastEmbed para embeddings locales multilingüe (paraphrase-multilingual-MiniLM-L12-v2, ~120MB)
- [x] Búsqueda semántica en historial — motor usa contexto relevante por contenido, no cronológico
- [x] `keel remember` — agrega notas y promesas al grafo de relaciones + LanceDB
- [x] `keel respond` indexa automáticamente cada conversación guardada

## Hito 3 — API REST (completado 2026-06-26)

- [x] FastAPI sobre keel-core: GET /status, GET+PUT /perfil, GET+POST /personas, POST /respond, POST /remember
- [x] `keel serve` arranca el servidor en localhost:7331
- [x] Documentación automática en /docs
- [x] 20/20 tests verde

## Hito 4 — Conector MCP (completado 2026-06-26)

- [x] Servidor MCP con FastMCP (mcp 1.28.1)
- [x] 5 herramientas: keel_get_context, keel_respond, keel_remember, keel_list_personas, keel_get_persona
- [x] 2 recursos: keel://perfil, keel://personas
- [x] `keel mcp` arranca el servidor en stdio (compatible con Claude Code)
- [x] .claude/mcp-config.json listo para conectar
- [x] 27/27 tests verde

## Hito 5 — Utilidades diarias y MCP Prompts (completado 2026-06-26)

- [x] `keel agenda` — tabla de compromisos pendientes con detección de vencidos
- [x] `keel contexto` — muestra el contexto de una persona sin generar respuesta
- [x] MCP Prompt `keel_responder` — template para Claude Code
- [x] MCP Prompt `keel_agenda_prompt` — agenda para revisar con el LLM
- [x] 36/36 tests verde

## Hito 6 — Instalador (completado 2026-06-26)

- [x] `install.sh` — 8 pasos: Python check, Ollama check, fuente, venv, binario, PATH, init, verify
- [x] Detecta instalación local vs descarga desde GitHub automáticamente
- [x] `uninstall.sh` — elimina app, preserva datos de usuario en ~/.keel/
- [x] `keel update` — git pull + reinstalación de dependencias
- [x] App en ~/.local/share/keel-core/, binario en ~/.local/bin/keel

## Hito 7 — keel conversar (completado 2026-06-26)

- [x] Flujo completo: mensaje → tono → contexto → sugerencia → editor → guardar
- [x] Soporta mensaje como argumento, stdin piped, o entrada interactiva
- [x] `--no-editar` y `--no-guardar` para uso programático/scripts
- [x] `keel.engine.sesion` como módulo puro testeable sin TTY
- [x] 46/46 tests verde

## Hito 8 — CI, release y herramientas dev (completado 2026-06-26)

- [x] GitHub Actions CI: tests en Python 3.11–3.13 + lint ruff en cada push/PR
- [x] GitHub Actions Release: auto-release en tags `v*`, corre tests antes de publicar
- [x] `Makefile`: atajos `make test`, `make lint`, `make serve`, `make mcp`, `make install`
- [x] Configuración ruff en `pyproject.toml` (E, F, W, I — sin E501)
- [x] `keel export` — genera contexto de personas como Markdown (stdout o archivo)

## Hito 9 — Loop de aprendizaje (completado 2026-06-26)

- [x] `SugerenciasPerfil` — modelo Pydantic para frases, vocabulario, valores, temas
- [x] `keel.engine.aprendizaje` — análisis puro: prompt → LLM → parseo robusto de JSON
- [x] `keel perfil show` — vuelca el perfil legible en tabla
- [x] `keel perfil actualizar` — analiza historial, sugiere item por item, aplica solo con confirmación
- [x] Parseo resiliente: extrae JSON de respuestas con texto adicional, fallback si falla
- [x] 56/56 tests verde

## Hito 10 — Cifrado en reposo (completado 2026-06-26)

- [x] `keel.security.cifrado` — AES-256-GCM con magic header `KEEL` para detección
- [x] `keel.security.llave` — clave random 32 bytes, Keychain (macOS) con fallback a `~/.keel/.key` (0600)
- [x] `storage/local.py` — wrapper transparente: cifra en write, descifra en read si `.cifrado` activo
- [x] `keel cifrar` — migración one-shot: activa cifrado y protege archivos existentes
- [x] `keel descifrar` — desactiva cifrado y restaura JSON a texto plano
- [x] Opt-in vía marker `~/.keel/.cifrado` — retrocompatible, no rompe instalaciones existentes
- [x] 67/67 tests verde

## Hito 11 — Canal clipboard (completado 2026-06-26)

- [x] `keel.io.clipboard` — `leer()` / `escribir()` vía `pbpaste`/`pbcopy` (sin deps nuevas)
- [x] `keel clip --remitente X` — flujo completo: clipboard → tono → sugerencia → devolver al clipboard
- [x] `--copiar` para auto-copiar sin confirmación (modo script/shortcut)
- [x] Errores claros si clipboard vacío, pbpaste/pbcopy falla, o plataforma no es macOS
- [x] 74/74 tests verde

## Hito 12 — Cero fricción (completado 2026-06-26)

- [x] Picker interactivo de persona — `keel clip` y `keel conversar` sin `--remitente` muestran tabla numerada con rol y última interacción
- [x] Selección por número, nombre exacto, o prefijo no ambiguo
- [x] `scripts/raycast/keel-clip.sh` — comando Raycast: si pasa remitente lo usa directamente; si no, abre Terminal con picker
- [x] `scripts/raycast/keel-conversar.sh` — abre flujo completo desde Raycast
- [x] 82/82 tests verde

## Hito 13 — Reflexión semanal (completado 2026-06-26)

- [x] `DigestRelacional` — modelo con promesas próximas, personas sin contacto, temas recurrentes
- [x] `keel.engine.reflexion` — lógica pura: detección de urgencias, cálculo de días, top temas por frecuencia
- [x] `keel reflexionar` — muestra el digest, síntesis LLM opcional, exporta a clipboard o archivo Markdown
- [x] `--sin-llm` para uso offline, `--clipboard` para Obsidian/notas, `--output` para archivo
- [x] Emojis de semáforo en promesas (🔴 ≤2d, 🟡 ≤5d, 🟢 resto)
- [x] 96/96 tests verde

## Hito 14 — Búsqueda en historial (completado 2026-06-26)

- [x] `keel.engine.busqueda` — motor puro: semántico (LanceDB) con fallback a keyword
- [x] `keel buscar "texto"` — tabla de resultados con persona, fecha, resumen, temas
- [x] `--persona X` para filtrar, `--top N` para limitar resultados, `--sin-vectores` para forzar keyword
- [x] Modo semántico activo si embedder disponible; keyword si no (sin error)
- [x] Resultados ordenados por fecha descendente
- [x] 108/108 tests verde

## Hito 15 — MCP actualizado (completado 2026-06-26)

- [x] `keel_buscar(texto, persona, top)` — búsqueda en historial desde Claude Code
- [x] `keel_reflexionar(dias_promesa, dias_silencio)` — digest semanal como tool MCP
- [x] `keel_aprender()` — sugerencias de perfil sin aplicarlas (read-only desde MCP)
- [x] Instructions del servidor actualizadas para incluir los nuevos tools
- [x] 113/113 tests verde

## Hito 16 — Importación de historial (completado 2026-06-26)

- [x] `keel.io.importar` — parsers para WhatsApp (iOS + Android), texto plano y CSV
- [x] Detección automática de formato (`--formato auto`)
- [x] Agrupación por día para WhatsApp (1 resumen por día, no un registro por mensaje)
- [x] Filtrado de mensajes del sistema (multimedia, cifrado, etc.)
- [x] `keel importar archivo.txt --persona Carlos` — preview + confirmación + indexación LanceDB
- [x] `--dry-run` para ver qué importaría sin escribir nada
- [x] Deduplicación por fecha al importar sobre historial existente
- [x] 132/132 tests verde

## Hito 17 — Gestión completa de personas (completado 2026-06-26)

- [x] `keel persona renombrar <viejo> <nuevo>` — actualiza archivo y campo nombre
- [x] `keel persona eliminar <nombre>` — con confirmación; `--forzar` para scripts
- [x] `keel persona editar <nombre>` — abre en $EDITOR, valida JSON al cerrar
- [x] `keel persona fusionar <origen> <destino>` — combina historial, promesas y sensibilidades; deduplica; ordena cronológicamente; elimina origen
- [x] `keel persona list` mejorado con columna de última interacción
- [x] 147/147 tests verde

## Hito 18 — Agenda completa + notificaciones macOS (completado 2026-06-26)

- [x] `keel agenda ver` — tabla con índice, estado (VENCIDA/HOY/PRÓXIMA) y semáforo visual
- [x] `keel agenda completar --persona X --indice N` — marca promesa cumplida; acepta --descripcion para búsqueda por texto
- [x] `keel agenda posponer --persona X --indice N --fecha YYYY-MM-DD` — cambia fecha límite
- [x] `keel agenda notificar` — notificaciones macOS vía osascript para promesas urgentes
- [x] `scripts/launchd/install-notificaciones.sh` — activa notificaciones automáticas a las 9am
- [x] 159/159 tests verde

## Hito 19 — Integración Obsidian (completado 2026-06-26)

- [x] `keel.io.obsidian` — write_nota, exportar_reflexion, exportar_persona, agregar_a_diario
- [x] Frontmatter YAML automático (tipo, fecha, tags) compatible con Obsidian
- [x] `keel reflexionar --obsidian [--vault PATH]` — escribe digest en `vault/keel/reflexiones/`
- [x] `keel exportar-obsidian [--remitente X]` — exporta personas como notas con checkboxes de promesas
- [x] `keel conversar --obsidian` — agrega resumen al diario del día en `vault/keel/diario/`
- [x] Vault default: `~/Proyectos/` (vault de Obsidian de Juan Diego)
- [x] 175/175 tests verde

## Hito 20 — REST API completa v0.2.0 (completado 2026-06-26)

- [x] `POST /buscar` — búsqueda keyword/semántica en historial con filtro por persona
- [x] `GET /reflexion` — digest relacional en JSON o Markdown; parámetros dias_promesa y dias_silencio
- [x] `GET /agenda` — lista de promesas pendientes con estado de vencimiento
- [x] `POST /agenda/{persona}/completar` — marca promesa cumplida por índice
- [x] `PATCH /agenda/{persona}/posponer` — cambia fecha límite de una promesa
- [x] `POST /aprendizaje/analizar` — análisis de historial vía LLM; retorna SugerenciasPerfil
- [x] API bumpeada a v0.2.0
- [x] 189/189 tests verde

## Hito 21 — `keel config` (completado 2026-06-26)

- [x] `ConfigKeel` — modelo Pydantic con 6 preferencias: vault_obsidian, modelo_ollama, dias_promesa, dias_silencio, min_conversaciones_aprendizaje, clipboard_no_guardar
- [x] `cargar_config()` / `guardar_config()` en `storage/local.py` — transparente al cifrado
- [x] `keel config ver` — tabla de preferencias actuales con descripción
- [x] `keel config set <clave> <valor>` — tipado correcto (int, bool, str), error claro en clave desconocida
- [x] `keel config reset` — restaura defaults con confirmación
- [x] Integración en `reflexionar` — `--dias-promesa` y `--dias-silencio` usan config como default
- [x] Integración en `conversar` — `--vault` y `--modelo` usan config como default
- [x] Integración en `clip` — `clipboard_no_guardar` activa `--no-guardar` automáticamente
- [x] 205/205 tests verde

## Hito 22 — `keel historial` (completado 2026-06-26)

- [x] `keel historial --persona X` — tabla cronológica de conversaciones con fecha, resumen y temas
- [x] `--desde` / `--hasta` para filtrar por rango de fechas (YYYY-MM-DD)
- [x] `--top N` para ver solo los N más recientes
- [x] `--json` para output procesable por scripts o LLMs
- [x] Ordenación cronológica garantizada (independiente del orden de inserción)
- [x] 216/216 tests verde

## Hito 23 — `keel preparar` (completado 2026-06-26)

- [x] `keel.engine.preparar` — motor puro: `briefing_a_markdown`, `construir_prompt_briefing`, `_temas_frecuentes`
- [x] `keel preparar --persona X` — briefing completo: rol, contexto, sensibilidades, estado actual, promesas, historial reciente, temas frecuentes
- [x] `--sin-llm` para briefing offline, `--recientes N` para controlar ventana de historial
- [x] Síntesis LLM en 3-5 líneas para lo más importante de la conversación
- [x] `--clipboard` para copiar, `--obsidian` para exportar a `vault/keel/briefings/`
- [x] Integra `cargar_config()` — vault y modelo desde config si no se pasan flags
- [x] 236/236 tests verde

## Hito 24 — `keel stats` (completado 2026-06-26)

- [x] `keel.engine.stats` — motor puro: personas activas, temas frecuentes, distribución por mes, promesas vencidas
- [x] `keel stats` — vista ejecutiva: totales globales, ranking de personas, nube de temas, histograma mensual de actividad, tabla de promesas vencidas
- [x] `--json` para output procesable por scripts o integración con otros sistemas
- [x] 249/249 tests verde

## Hito 25 — MCP v2 (completado 2026-06-26)

- [x] `keel_preparar(persona, n_recientes)` — briefing pre-conversación desde Claude Code
- [x] `keel_historial(persona, desde, hasta, top)` — historial cronológico con filtros desde Claude Code
- [x] `keel_stats()` — panorama estadístico del grafo desde Claude Code
- [x] Instructions del servidor actualizadas con los nuevos tools
- [x] MCP ahora tiene 11 tools: get_context, respond, remember, list_personas, get_persona, buscar, reflexionar, aprender, preparar, historial, stats
- [x] 258/258 tests verde (237 rápidos + 21 MCP)

## Hito 26 — `keel agenda add` (completado 2026-06-26)

- [x] `keel agenda add --persona X --descripcion "..." [--fecha YYYY-MM-DD]` — agrega promesa directamente sin prefijo mágico
- [x] Validación de fecha, acumulación correcta sobre promesas existentes
- [x] `keel_agenda_add(persona, descripcion, fecha)` — tool MCP para registrar compromisos desde Claude Code
- [x] MCP ahora tiene 12 tools
- [x] 265/265 tests verde (241 rápidos + 24 MCP)

## Hito 27 — `keel persona show` enriquecido (completado 2026-06-26)

- [x] Vista de perfil completa: rol, contexto, tono, sensibilidades, estado actual
- [x] Días transcurridos desde última interacción (calculado en tiempo real)
- [x] Sección "Temas frecuentes" — solo temas con más de 1 mención, con contador
- [x] Tabla de compromisos pendientes con semáforo 🔴🟡🟢 por fecha
- [x] Historial reciente con `--recientes N` (default 5), muestra total si hay más
- [x] `--raw` para mantener el dump JSON original cuando se necesite
- [x] 271/271 tests verde (247 rápidos + 24 MCP)

## Hito 28 — `keel hoy` (completado 2026-06-26)

- [x] `keel hoy` — conversaciones guardadas hoy + promesas con fecha hoy, por persona
- [x] `--fecha YYYY-MM-DD` para revisar cualquier día pasado
- [x] Conteo final: X conversaciones · Y promesas · Z personas
- [x] `--clipboard` para copiar el resumen en Markdown
- [x] `--obsidian` para agregar al diario del día en el vault
- [x] Integra `cargar_config()` para vault por defecto
- [x] 281/281 tests verde (257 rápidos + 24 MCP)

## Hito 29 — `keel backup` / `keel restaurar` (completado 2026-06-26)

- [x] `keel backup [--output PATH]` — ZIP de todo `~/.keel/` con fecha en el nombre, sin deps nuevas
- [x] `keel restaurar ARCHIVO.zip [--forzar]` — extrae sobre `~/.keel/`, confirmación antes de sobreescribir
- [x] Funciona transparentemente con datos cifrados y sin cifrar
- [x] 291/291 tests verde (267 rápidos + 24 MCP)

## Hito 30 — `keel status` mejorado (completado 2026-06-26)

- [x] Versión del paquete vía `importlib.metadata`
- [x] Nombre del usuario del perfil en la línea de estado
- [x] Total de conversaciones + promesas pendientes a nivel global
- [x] Última actividad registrada (máximo de `ultima_interaccion` entre todas las personas)
- [x] Sección de config activa: vault Obsidian, días promesa/silencio
- [x] Estado de cifrado AES-256-GCM (activo/inactivo)
- [x] Tamaño total de `~/.keel/` en KB/MB
- [x] 303/303 tests verde (279 rápidos + 24 MCP)

## Hito 31 — `keel buscar` con filtros de fecha (completado 2026-06-26)

- [x] `buscar_global()` acepta `desde`/`hasta` como filtros post-búsqueda en ambos modos (semántico y keyword)
- [x] `keel buscar "texto" --desde 2026-01-01 --hasta 2026-06-30` — búsqueda cross-persona con rango de fechas
- [x] Validación de formato YYYY-MM-DD en el CLI con error claro
- [x] MCP `keel_buscar` actualizado con parámetros `desde`/`hasta`; mensaje de "sin resultados" incluye el rango aplicado
- [x] 308/308 tests verde (284 rápidos + 24 MCP)

## Hito 32 — `keel sugerir` (completado 2026-06-26)

- [x] `keel.engine.sugerencias` — motor puro: scoring por urgencia (vencidas ×100+días, próximas ×50-días, silencio ×días), temas frecuentes como contexto
- [x] `keel sugerir [--top N] [--sin-llm] [--clipboard]` — lista priorizada con razones concretas por contacto
- [x] Respeta `config.dias_silencio` y `config.dias_promesa` para los umbrales
- [x] Síntesis LLM en 2-4 líneas de qué priorizar esta semana
- [x] `keel_sugerir(top)` como tool MCP — 13 tools en total
- [x] 324/324 tests verde (300 rápidos + 24 MCP)

## Hito 33 — Polish de subgrupos (completado 2026-06-26)

- [x] `keel perfil editar` — abre `perfil.json` en `$EDITOR`, valida JSON al cerrar (mirror de `keel persona editar`)
- [x] `keel agenda ver --persona X` — filtra la vista de agenda por persona; sin `--persona` sigue mostrando todo
- [x] 332/332 tests verde (308 rápidos + 24 MCP)

## Hito 34 — Instalador actualizado (completado 2026-06-27)

- [x] `install.sh` actualizado a v0.2.0: fix bug PATH_UPDATED, "próximos pasos" con comandos actuales (`keel conversar`, `keel hoy`, `keel sugerir`, MCP con sintaxis correcta)
- [x] Aviso de descarga fastembed (~90MB en primer `keel buscar`)
- [x] `uninstall.sh` — ofrece backup automático con `keel backup` antes de desinstalar
- [x] `keel init` — mensaje corregido de `keel respond` a `keel conversar`

## Hito 35 — `keel pregunta` (completado 2026-06-27)

- [x] `keel.engine.pregunta` — motor puro: `construir_prompt_pregunta`, `respuesta_sin_llm`
- [x] `keel pregunta "¿...?" --persona X` — busca fragmentos relevantes del historial y los da como contexto al LLM para responder
- [x] `--sin-llm` para ver el historial relevante sin síntesis
- [x] Fallback si Ollama no disponible: muestra historial sin síntesis con aviso
- [x] `--clipboard` para copiar la respuesta
- [x] `--sin-vectores`, `--top N`, `--modelo M` para control fino
- [x] Picker de persona si se omite `--persona`
- [x] `keel_pregunta(pregunta, persona, top)` — tool MCP: 14 tools en total
- [x] 340/340 tests verde (324 rápidos + 16 pregunta + 27 MCP — 3 nuevos)

## Hito 36 — `keel pregunta` modo global (completado 2026-06-27)

- [x] `keel pregunta "¿...?"` sin `--persona` — busca en el historial de todas las personas
- [x] Prompt diferenciado: modo global muestra nombre de la persona en cada fragmento
- [x] `respuesta_sin_llm` adaptado: etiqueta `[persona]` en cada resultado del modo global
- [x] `keel_pregunta` MCP: `persona=""` (vacío) activa modo global
- [x] 331/331 tests rápidos verde (7 tests nuevos en test_pregunta.py)

## Hito 37 — `keel volcar` (completado 2026-06-27)

- [x] `keel.engine.volcado` — motor puro: `volcar_a_markdown`, `_icono_promesa` (🔴🟡🟢 por urgencia)
- [x] `keel volcar` — dump completo: framing LLM + perfil + personas (N recientes) + agenda global con semáforos
- [x] `--persona X` para volcar solo una persona, `--recientes N` (default 3), `--sin-framing`, `--clipboard`, `--output`
- [x] Diferencia con `keel export`: framing instruccional, agenda consolidada, semáforos de urgencia, orientado a Claude.ai
- [x] 351/351 tests verde (20 tests nuevos en test_volcado.py)

## Hito 38 — `keel notas` (completado 2026-06-27)

- [x] `Nota` — modelo Pydantic: id (UUID 8 chars), fecha (auto), contenido, temas
- [x] `cargar_notas`, `guardar_notas`, `agregar_nota`, `eliminar_nota` en `storage/local.py`
- [x] `buscar_notas(texto, notas, embedder, top)` en `engine/busqueda.py` — keyword + semántico; devuelve `persona="[nota]"`
- [x] `keel notas add "contenido" [--temas a,b]` — agrega nota e indexa en LanceDB (`persona="_notas"`)
- [x] `keel notas ver [--top N] [--desde YYYY-MM-DD]` — tabla cronológica
- [x] `keel notas buscar "texto"` — búsqueda keyword/semántica en notas
- [x] `keel notas borrar ID [--forzar]` — elimina por ID con confirmación
- [x] `keel pregunta` (global) incluye notas automáticamente en el contexto de búsqueda
- [x] 375/375 tests verde (24 tests nuevos en test_notas.py)

## Hito 39 — MCP para notas (completado 2026-06-27)

- [x] `keel_notas_add(contenido, temas)` — captura una nota desde Claude Code e indexa en LanceDB
- [x] `keel_notas_buscar(texto, top)` — busca en notas por contenido/tema (semántico + keyword)
- [x] `keel_notas_ver(top)` — lista las notas más recientes con ID, fecha y temas
- [x] `keel_pregunta` MCP actualizado: modo global incluye notas en la búsqueda de contexto
- [x] Instructions del servidor MCP actualizadas con los nuevos tools
- [x] MCP ahora tiene 17 tools en total
- [x] 375 rápidos + tests MCP nuevos verde

## Hito 40 — README + keel volcar con notas (completado 2026-06-27)

- [x] README completo: instalación, quick start, referencia de todos los comandos, tabla MCP (17 tools), flujos típicos, estructura de datos, privacidad, desarrollo
- [x] `Makefile` separado en `make test` (rápidos) y `make test-all` (incluye MCP)
- [x] `keel volcar` incluye sección "Notas recientes" cuando hay notas (`--sin-notas` para omitir, `--notas-top N`)
- [x] `keel volcar --persona X` correctamente omite notas (son globales, no de una persona)
- [x] 380/380 tests verde (5 tests nuevos en test_volcado.py)

## Hito 41 — `keel alias` (completado 2026-06-27)

- [x] `cargar_aliases`, `guardar_aliases`, `resolver_alias` en `storage/local.py` — persistencia en `~/.keel/aliases.json`
- [x] `cargar_persona()` resuelve aliases automáticamente — todos los comandos con `--persona` se benefician sin cambios
- [x] `keel alias add <atajo> <persona>` — crea o actualiza alias; avisa si ya existe una persona con ese nombre
- [x] `keel alias list` — tabla de todos los aliases definidos con contador
- [x] `keel alias borrar <atajo>` — elimina alias con error claro si no existe
- [x] Resolución case-insensitive (`jc`, `JC`, `Jc` → mismo alias)
- [x] 20 tests nuevos en `tests/test_alias.py`
- [x] 400/400 tests verde

## Hito 42 — `keel notas editar` + MCP alias (completado 2026-06-27)

- [x] `keel notas editar <id> [--contenido "..."] [--temas "..."]` — edita contenido y/o temas de una nota; sin flags abre en `$EDITOR`
- [x] Preserva `id` y `fecha` original al editar
- [x] 5 tests nuevos en `test_notas.py` cubriendo flags, preservación de fecha e ID inválido
- [x] `keel_alias_add(alias, persona)` — crea o actualiza alias desde Claude Code
- [x] `keel_alias_list()` — lista aliases definidos
- [x] `keel_alias_borrar(alias)` — elimina alias con error claro si no existe
- [x] `keel_alias_*` registrados en `list_tools` y en `instructions` del servidor MCP
- [x] MCP ahora tiene 20 tools en total
- [x] 5 tests nuevos en `test_mcp.py`
- [x] 405 rápidos + 37 MCP = 442 tests verde

## Hito 43 — `keel agenda borrar` + `keel persona tag` (completado 2026-06-27)

- [x] `keel agenda borrar --persona X (--indice N | --descripcion "...")` — elimina una promesa sin marcarla cumplida; `--forzar` para scripts
- [x] 8 tests nuevos en `test_agenda.py`: por índice, por descripción, índice inválido, sin coincidencia, sin promesas, ambiguo, sin argumento
- [x] Campo `tags: list[str]` añadido al modelo `Persona` (retrocompatible — default `[]`)
- [x] `keel persona tag add <nombre> <tag>` — añade etiqueta (normaliza a minúscula, no duplica)
- [x] `keel persona tag borrar <nombre> <tag>` — elimina etiqueta con error claro si no existe
- [x] `keel persona tag list [tag]` — sin arg: personas con etiquetas; con arg: filtra por etiqueta
- [x] `keel persona list --tag <tag>` — columna Tags añadida, filtro opcional
- [x] 10 tests nuevos en `test_persona_mgmt.py`
- [x] 420 rápidos verde

## Hito 44 — Síntesis relacional inferida (completado 2026-06-27)

Primer paso del paradigma emergente: Keel infiere quién es cada persona
sin que el usuario tenga que clasificarla explícitamente.

- [x] `Persona` con 4 nuevos campos: `narrativa`, `tipo_relacion`, `contexto_situacional`, `ultima_sintesis`
- [x] `keel.engine.sintesis` — motor puro: `construir_prompt_sintesis`, `parsear_sintesis` (robusto ante ruido), `sintetizar_persona`, `aplicar_sintesis`
- [x] 8 tipos de relación inferibles: familia | amistad | trabajo | cliente | colaborador | mentor | nuevo | otro
- [x] `keel persona sintetizar <nombre>` — infiere narrativa de una persona usando Ollama
- [x] `keel persona sintetizar` (sin arg) — sintetiza todas las personas con historial; omite las ya sintetizadas hoy (salvo `--forzar`)
- [x] `keel persona show` muestra la síntesis como panel al inicio si existe
- [x] `keel volcar` incluye narrativa y contexto situacional como blockquote Markdown por persona
- [x] `keel_sintetizar_persona(persona)` — tool MCP (21 tools en total)
- [x] Parseo resiliente: extrae JSON aunque la respuesta traiga texto adicional; fallback a narrativa cruda si falla
- [x] 22 tests en `tests/test_sintesis.py` (prompt, parseo, motor puro, CLI, show, volcado)
- [x] 442 rápidos verde

## Hito 45 — Ciclo de síntesis autónomo nocturno (completado 2026-06-27)

- [x] `keel ciclo` — comando diseñado para launchd: sintetiza todas las personas con historial, registra en `~/.keel/logs/ciclo.log` con timestamps
- [x] Salida limpia si Ollama no disponible (exit 0, launchd no marca el job como fallido)
- [x] `--dry-run` muestra qué personas se sintetizarían sin modificar datos
- [x] `--forzar` re-sintetiza aunque ya tenga síntesis del día
- [x] `--ver-log` muestra las últimas 40 líneas del log desde la terminal
- [x] Omite automáticamente personas sin historial y ya sintetizadas hoy
- [x] `scripts/launchd/install-ciclo.sh` — instala launchd agent a las 2:00 AM (hora configurable como argumento)
- [x] `EnvironmentVariables.PATH` en el plist incluye Homebrew y `~/.local/bin` para que keel sea encontrable por launchd
- [x] 13 tests en `tests/test_ciclo.py`: flujo completo, log, dry-run, forzar, Ollama caído, ver-log, sin perfil
- [x] 455 rápidos verde
## Hito 46 — Integración con Calendario de macOS (completado 2026-06-28)

- [x] `keel.io.calendario` — lee eventos próximos vía osascript (sin OAuth ni dependencias externas)
- [x] `inferir_contexto_agenda(eventos, dias)` — detecta patrones situacionales por keywords en títulos (temporada electoral, lanzamiento, viaje, etc.)
- [x] `resumir_agenda(eventos, dias)` — texto comprimido de la agenda para incluir en prompts LLM
- [x] `sintetizar_persona` acepta `contexto_agenda` — el ciclo nocturno lo pasa automáticamente al prompt de síntesis
- [x] `keel ciclo` lee el calendario antes de sintetizar — el contexto situacional se enriquece con la agenda real
- [x] `keel calendario [--dias N] [--contexto]` — comando CLI: tabla de eventos + contexto inferido
- [x] `keel_calendario_ver(dias)` — tool MCP: resumen de eventos + contexto (22 tools en total)
- [x] `keel_calendario_contexto(dias)` — tool MCP: solo el contexto situacional (para prompts de síntesis)
- [x] Falla silenciosamente si no es macOS o si osascript no devuelve datos
- [x] 78 tests verde (calendario + MCP + ciclo)

## Hito 47 — Abstracción FuenteMensajes (completado 2026-06-28)

- [x] `FuenteMensajes` (ABC) en `src/keel/io/fuentes.py` — contrato: `nombre`, `extensiones`, `leer()`, `agrupar()`
- [x] `ExportacionWhatsApp` — wraps el parser existente de `importar.py`
- [x] `TextoPlano` — párrafos separados por línea en blanco
- [x] `CSV` — columnas fecha, resumen [, temas]
- [x] `detectar_fuente()` — autodetección por extensión y contenido (patrón WhatsApp en primeros 500 chars)
- [x] `fuente_para_formato()` — instancia por nombre explícito, case-insensitive
- [x] `MensajeImportado` migrado a `fuentes.py`; re-exportado desde `importar.py` (retrocompatible)
- [x] `keel importar` usa `detectar_fuente` / `fuente_para_formato` en lugar de if/elif hardcodeados
- [x] 30 tests nuevos en `tests/test_fuentes.py`; `tests/test_importar.py` sin modificar (retrocompat verificada)
- [x] 469 tests rápidos verde

## Hito 48 — Cloud LLM opt-in (pendiente)

## Diferido / fuera de scope inicial

- Conector WhatsApp real — riesgo regulatorio y técnico alto (FuenteMensajes es el contrato; la impl. real queda diferida)
- Sincronización cloud de ~/.keel/ con E2E entre dispositivos
- Windows support
