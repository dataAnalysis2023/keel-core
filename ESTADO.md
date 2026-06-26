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
