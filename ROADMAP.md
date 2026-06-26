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

## Hito 4 — Conectividad MCP

- [ ] Servidor MCP genérico en keel-core
- [ ] Primer conector de mensajería (a definir — no WhatsApp en esta fase)
- [ ] Cifrado de base de datos (SQLCipher via SQLCipher3)

## Diferido / fuera de scope inicial

- Conector WhatsApp — riesgo regulatorio y técnico alto, no bloquea el núcleo
- Modo cloud opt-in con cifrado E2E
- Windows support
