---
proyecto: keel-core
tipo: contexto
estado: activo
---

# CLAUDE.md — keel-core

## Qué es
Motor de extensión cognitiva personal. Librería Python pura que mantiene el contexto del usuario —quién eres, cómo piensas, con quién hablas— para generar sugerencias de respuesta fieles a tu voz usando LLM local vía Ollama. Nace como herramienta personal de Juan Diego / Imagine Robots.

## Stack
- **Python 3.11+** — librería pura, sin framework web
- **Pydantic v2** — modelos de dominio
- **httpx** — cliente HTTP para Ollama (síncrono en Hito 1)
- **Typer + Rich** — CLI
- **Ollama** — inferencia local (Llama 3, Mistral, Phi-3)
- **pytest** — tests unitarios

## Estructura del paquete
```
src/keel/
  models/
    perfil.py      PerfilUsuario — voz, valores, contexto vital (Módulo 1)
    persona.py     Persona — historial, promesas, tono relacional (Módulo 2)
  engine/
    presencia.py   Capa Présence: análisis heurístico de tono emocional
    respuesta.py   Motor de respuesta: construye prompt + llama LLM (Módulo 3)
  llm/
    base.py        Interfaz abstracta LLMBase
    ollama.py      Implementación Ollama
  storage/
    local.py       Carga/guarda JSON desde ~/.keel/
  cli/
    main.py        Comandos: respond | init | status
tests/
  fixtures/        JSON de ejemplo para PerfilUsuario y Persona
```

## Datos del usuario — ~/.keel/
```
~/.keel/
  perfil.json        PerfilUsuario serializado
  personas/
    carlos.json      Una Persona por remitente conocido
    maria.json
```

## Comandos
```bash
keel init                                          # crea ~/.keel/perfil.json de ejemplo
keel status                                        # Ollama + perfil + personas
keel respond "mensaje" --remitente Carlos          # genera sugerencia de respuesta
keel respond "mensaje" --remitente Carlos --modelo mistral
```

## Principios de diseño (no negociables)
1. **El usuario es el autor** — Keel sugiere, nunca decide
2. **Local primero** — Ollama, sin APIs externas por defecto
3. **El contexto es el producto** — la calidad viene del perfil, no del modelo
4. **keel-core ≠ keel-app** — separación estricta: esta librería no tiene UI

## Convenciones
- Idioma: español en nombres de dominio, comentarios y docs
- Commits: conventional commits (feat:, fix:, chore:, docs:)
- Fechas: YYYY-MM-DD
- Tests: pytest, sin mocks de LLM en tests unitarios del motor
