# Acceso Rápido — keel-core

## Qué es
Motor de extensión cognitiva personal. Librería Python que genera sugerencias de respuesta fieles a tu voz usando LLM local (Ollama). Primera capa del ecosistema Keel / Présence.

## Cómo abrir
```bash
cd /Users/juandcs/Proyectos/keel-core && claude --rc
```

## Instalación
```bash
pip install -e ".[dev]"
keel init      # crea ~/.keel/perfil.json
keel status    # verifica Ollama + perfil
```

## Uso básico
```bash
keel respond "Hola, ¿cómo vas con el prototipo?" --remitente Carlos
```

## Estado
Activo — Hito 1 scaffoldeado (2026-06-26). Pendiente: prueba end-to-end con Ollama.

## Stack
Python 3.11 · Pydantic v2 · httpx · Typer · Ollama

## Estructura del paquete
```
src/keel/
  models/    perfil.py · persona.py
  engine/    presencia.py · respuesta.py
  llm/       base.py · ollama.py
  storage/   local.py
  cli/       main.py
tests/
  fixtures/  perfil_usuario.json · persona_ejemplo.json
```
