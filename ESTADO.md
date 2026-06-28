---
proyecto: keel-core
tipo: estado
estado: activo
---

# ESTADO — keel-core

> Registro cronológico de sesiones. El estado actual y el plan por fases viven en `ROADMAP.md`.

---

## 2026-06-26 — Scaffold del Hito 1

**Contexto.** Proyecto greenfield nacido del documento de arquitectura "BLOQUE DE ARQUITECTURA — KEEL — Junio 2026". Primera sesión de desarrollo.

**Decisiones selladas.**
- Librería Python pura como primera capa. Sin interfaz gráfica, sin base de datos vectorial en el Hito 1 — solo el motor mínimo funcional.
- `src/` layout moderno para el paquete Python (evita conflictos de importación en desarrollo).
- Pydantic v2 para modelos de dominio — validación estricta y serialización JSON nativa.
- httpx síncrono para Ollama en el Hito 1. Asyncio entra cuando la UI lo justifique.
- Nombres de dominio en español (`perfil`, `persona`, `tono`, `presencia`) — el código colombiano habla su idioma.
- `~/.keel/` como directorio de datos del usuario, separado del repo.
- Separación estricta keel-core (motor) ≠ keel-app (interfaz futura) desde el primer commit.
- Capa Présence como análisis heurístico en el Hito 1 — suficiente para el flujo mínimo; el Hito 2 puede reemplazarlo con una llamada LLM dedicada si la calidad lo justifica.

**Ejecutado.** Scaffold completo del Hito 1:
- `src/keel/models/perfil.py` — PerfilUsuario con VozUsuario, CoherenciaRegistro
- `src/keel/models/persona.py` — Persona con historial, promesas, tono relacional
- `src/keel/engine/presencia.py` — análisis heurístico de tono (urgencia, emocionalidad, formalidad, tensión)
- `src/keel/engine/respuesta.py` — Motor: construye prompt con contexto completo, llama LLM
- `src/keel/llm/base.py` + `ollama.py` — abstracción + implementación Ollama
- `src/keel/storage/local.py` — carga/guarda JSON desde `~/.keel/`
- `src/keel/cli/main.py` — comandos `respond`, `init`, `status`
- `tests/fixtures/` — datos de ejemplo para tests
- `pyproject.toml` — configuración del paquete con hatchling

**Pendiente del Hito 1.** Verificar instalación `pip install -e .` y prueba end-to-end con Ollama real.

---

## 2026-06-28 — Hito 46: integración Calendario de macOS

**Decisiones selladas.**
- Calendario vía `osascript` (JXA) en lugar de Google Calendar API — sin OAuth, sin credenciales externas, funciona con cualquier fuente sincronizada en la app Calendario (iCloud, Google, Outlook). Falla silenciosamente si no está disponible.
- `_KEYWORDS_CONTEXTO` usa frases compuestas ("campaña electoral") en lugar de palabras sueltas ("campaña") para reducir falsos positivos en títulos de reuniones comunes.
- El contexto de agenda se pasa al ciclo nocturno como string ya formateado — `sintetizar_persona` no depende del calendario, solo lo consume opcionalmente.

**Ejecutado.**
- `src/keel/io/calendario.py` — EventoCalendario, leer_eventos_macos, resumir_agenda, inferir_contexto_agenda
- `src/keel/engine/sintesis.py` — `construir_prompt_sintesis` acepta `contexto_agenda`; `sintetizar_persona` lo propaga
- `src/keel/cli/main.py` — `keel ciclo` lee calendario antes de sintetizar; comando `keel calendario`
- `src/keel/mcp/server.py` — `keel_calendario_ver`, `keel_calendario_contexto` (22 tools en total)
- `tests/test_calendario.py` — 245 líneas, mockea osascript vía monkeypatch
- 78 tests verde al cierre de sesión

**Estado al cierre.** Hitos 1–46 completados. 78 tests verde. Sistema en producción local (launchd ciclo nocturno activo). Próxima área: pendiente de definir.

---

## 2026-06-28 — Hitos 47–50: FuenteMensajes, Cloud LLM, keel SOS y PWA

**Decisiones selladas.**
- Hito 47: `FuenteMensajes` (ABC) como contrato para fuentes externas. WhatsApp, TextoPlano y CSV como primeras implementaciones. `keel importar` usa `detectar_fuente()` en lugar de if/elif hardcodeados.
- Hito 48: Cloud LLM opt-in. `AnthropicLLM` y `OpenAILLM` implementan `LLMBase` con lazy import. `crear_llm(config)` reemplaza todas las instancias directas de `OllamaLLM`. API keys en Keychain. `keel api-key set|get|borrar`.
- Hito 49: `keel sos` genera archivo `.ksos` (ZIP+AES-256-GCM, PBKDF2 260k iter) con contexto completo de una persona. Diseñado para el flujo SOS: usuario en cama, no sabe qué responder, activa el botón de emergencia.
- Hito 50: PWA `keel SOS` en `web/`. Descifra `.ksos` en el browser con WebCrypto (ningún dato sale del dispositivo). Offline-capable via Service Worker. Deployada en `keel-sos.vercel.app`.
- Repo publicado en GitHub: `github.com/dataAnalysis2023/keel-core`.
- Pronunciación confirmada: **"quil"** (no "kel", no dos sílabas).

**Ejecutado.**
- `src/keel/io/fuentes.py` — FuenteMensajes, ExportacionWhatsApp, TextoPlano, CSV, detectar_fuente
- `src/keel/llm/anthropic.py`, `openai_llm.py`, `factory.py` — proveedores cloud
- `src/keel/security/api_keys.py` — Keychain + fallback archivo 0600
- `src/keel/io/sos.py` — construir_paquete, cifrar_sos, descifrar_sos, guardar_sos
- `web/` — index.html, app.js, style.css, manifest.json, sw.js, icon.svg
- 515 tests rápidos verde al cierre

**Estado al cierre.** Hitos 1–50 completados. 515 tests rápidos verde. PWA en producción (keel-sos.vercel.app). Repo público en GitHub. Próximo paso: prueba end-to-end del flujo SOS completo en el celular.
