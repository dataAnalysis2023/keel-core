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
- [ ] Instalación `pip install -e .` verificada end-to-end
- [ ] Prueba real con Ollama corriendo

## Hito 2 — Contexto vectorial

- [ ] Integrar LanceDB para embeddings locales (evaluar vs ChromaDB)
- [ ] Búsqueda semántica en historial de conversaciones
- [ ] Módulo 4: actualización automática del grafo de relaciones tras respuesta aprobada
- [ ] Comando `keel remember` para agregar notas manualmente

## Hito 3 — Interfaz desktop (keel-app)

- [ ] Evaluar Tauri vs Electron (preferencia: Tauri — más liviano, Rust + WebView)
- [ ] Panel de sugerencia con edición inline
- [ ] Vista del grafo de relaciones
- [ ] API interna REST entre keel-core y keel-app

## Hito 4 — Conectividad MCP

- [ ] Servidor MCP genérico en keel-core
- [ ] Primer conector de mensajería (a definir — no WhatsApp en esta fase)
- [ ] Cifrado de base de datos (SQLCipher via SQLCipher3)

## Diferido / fuera de scope inicial

- Conector WhatsApp — riesgo regulatorio y técnico alto, no bloquea el núcleo
- Modo cloud opt-in con cifrado E2E
- Windows support
