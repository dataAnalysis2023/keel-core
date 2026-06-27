# keel-core

Motor de extensión cognitiva personal — local first, sin APIs externas.

Keel mantiene el contexto de tus relaciones (quién eres, cómo piensas, con quién hablas) y usa un LLM local vía [Ollama](https://ollama.ai) para ayudarte a redactar respuestas fieles a tu voz, recordar acuerdos, preparar conversaciones y mantener el ritmo relacional.

---

## Requisitos

- Python 3.11+
- [Ollama](https://ollama.ai) corriendo localmente (`ollama serve`)
- macOS (Linux compatible; Windows no probado)

---

## Instalación

```bash
# Desde el repositorio local
bash install.sh

# Primera vez que uses búsqueda semántica, fastembed descarga ~90MB
keel buscar "prueba"
```

El instalador crea el entorno virtual, enlaza el binario en `~/.local/bin/keel` y ejecuta `keel init`.

Para desinstalar (preserva tus datos en `~/.keel/`):

```bash
bash uninstall.sh
```

---

## Inicio rápido

```bash
# 1. Inicializar y editar tu perfil
keel init
keel perfil editar        # abre en $EDITOR

# 2. Agregar una persona
keel persona add Carlos --rol "Director de Producto" --contexto "cofundador anterior"

# 3. Primera conversación
keel conversar "Hola, ¿cómo vas con el lanzamiento?" --persona Carlos

# 4. Ver tu agenda
keel agenda ver

# 5. Resumen del día
keel hoy
```

---

## Referencia de comandos

### Conversación

| Comando | Descripción |
|---------|-------------|
| `keel conversar "msg" --persona X` | Mensaje → tono → sugerencia → editor → guardado |
| `keel clip --persona X` | Lee del clipboard, devuelve sugerencia al clipboard |
| `keel respond "msg" --persona X` | Sugerencia directa sin flujo interactivo |

### Personas

```bash
keel persona add Nombre --rol "rol" --contexto "cómo os conocéis"
keel persona list
keel persona show Nombre          # vista completa con historial y promesas
keel persona editar Nombre        # abre en $EDITOR
keel persona renombrar Viejo Nuevo
keel persona eliminar Nombre
keel persona fusionar Origen Destino
```

### Agenda y compromisos

```bash
keel agenda ver                   # todas las promesas pendientes
keel agenda ver --persona Carlos  # filtrado por persona
keel agenda add --persona X --descripcion "..." --fecha 2026-08-01
keel agenda completar --persona X --indice 0
keel agenda posponer --persona X --indice 0 --fecha 2026-09-01
keel agenda notificar             # notificaciones macOS para promesas urgentes
```

### Memoria y búsqueda

```bash
keel remember "Acordamos entregar el prototipo en julio" --persona Carlos
keel buscar "prototipo"                        # búsqueda semántica/keyword
keel buscar "legal" --persona Ana --desde 2026-01-01
keel historial --persona Carlos --top 10
keel pregunta "¿qué acordamos sobre el proyecto?" --persona Carlos
keel pregunta "¿con quién hablé de temas legales?"   # búsqueda global
keel hoy                                       # actividad del día actual
keel hoy --fecha 2026-06-15
```

### Notas personales

```bash
keel notas add "Decidí no renovar el contrato" --temas "legal,decisión"
keel notas ver
keel notas ver --top 20 --desde 2026-06-01
keel notas buscar "contrato"
keel notas borrar <id>
```

Las notas aparecen automáticamente en `keel pregunta` (modo global).

### Síntesis y reflexión

```bash
keel sugerir                      # quién contactar hoy y por qué
keel preparar --persona Carlos    # briefing pre-conversación
keel reflexionar                  # digest semanal de relaciones
keel stats                        # panorama estadístico del grafo
```

### Perfil

```bash
keel perfil show
keel perfil editar                # abre perfil.json en $EDITOR
keel perfil actualizar            # analiza historial y sugiere actualizaciones
```

### Contexto para LLMs externos

```bash
keel volcar                       # dump completo para Claude.ai
keel volcar --persona Carlos      # solo una persona
keel volcar --clipboard           # copia directamente al portapapeles
keel volcar --recientes 5         # N conversaciones por persona (default: 3)
keel volcar --output contexto.md  # guarda en archivo
keel export                       # export básico de personas (sin framing LLM)
keel exportar-obsidian            # exporta a vault de Obsidian
```

### Datos y backup

```bash
keel backup                       # ZIP de ~/.keel/ con fecha
keel backup --output ~/backups/keel.zip
keel restaurar archivo.zip
keel importar chats.txt --persona Carlos   # importa historial WhatsApp/CSV/texto
keel cifrar                       # activa cifrado AES-256-GCM (opt-in)
keel descifrar                    # desactiva cifrado
```

### Sistema

```bash
keel status                       # estado: versión, Ollama, personas, config
keel config ver
keel config set modelo_ollama qwen2.5-coder:7b
keel config set dias_silencio 21
keel update                       # actualiza desde git
```

---

## Integración con Claude Code (MCP)

```bash
# Registrar el servidor MCP
claude mcp add keel -- keel mcp

# Verificar
claude mcp list
```

### Tools disponibles (17)

| Tool | Descripción |
|------|-------------|
| `keel_get_context` | Contexto relacional de una persona |
| `keel_respond` | Sugerencia de respuesta |
| `keel_remember` | Registrar conversación o promesa |
| `keel_list_personas` | Listar personas |
| `keel_get_persona` | Datos completos de una persona |
| `keel_buscar` | Búsqueda en historial |
| `keel_pregunta` | Pregunta al LLM con historial como contexto |
| `keel_reflexionar` | Digest semanal relacional |
| `keel_aprender` | Sugerencias de actualización del perfil |
| `keel_preparar` | Briefing pre-conversación |
| `keel_historial` | Historial cronológico con filtros |
| `keel_stats` | Estadísticas del grafo |
| `keel_agenda_add` | Registrar promesa con fecha |
| `keel_sugerir` | Sugerencias de contacto por urgencia |
| `keel_notas_add` | Capturar nota personal |
| `keel_notas_buscar` | Buscar en notas |
| `keel_notas_ver` | Listar notas recientes |

---

## Flujos típicos

### Mañana (2 min)
```bash
keel hoy          # qué pasó ayer
keel sugerir      # a quién contactar
keel agenda ver   # promesas urgentes
```

### Antes de una reunión
```bash
keel preparar --persona Carlos
# O desde Claude Code: keel_preparar(persona="Carlos")
```

### Después de una conversación
```bash
keel conversar "Su mensaje..." --persona Carlos
# El historial queda guardado e indexado automáticamente
```

### Capturar una decisión propia
```bash
keel notas add "Decidimos posponer el lanzamiento a Q4" --temas "producto,decisión"
# O desde Claude Code: keel_notas_add("Decidimos posponer...")
```

### Usar keel con Claude.ai (sin MCP)
```bash
keel volcar --clipboard
# Pega el contexto en la conversación de Claude.ai
```

### Revisión semanal
```bash
keel reflexionar --clipboard   # genera digest y copia a portapapeles
keel stats
```

---

## Estructura de datos

```
~/.keel/
  perfil.json          Voz, valores, contexto vital del usuario
  config.json          Preferencias (modelo, vault, umbrales)
  notas.json           Notas personales
  personas/
    carlos.json        Historial, temas, promesas por persona
    ana.json
  vectorial/           Índice LanceDB para búsqueda semántica
  .cifrado             Marker de cifrado AES-256-GCM (si activo)
```

---

## Privacidad

Todo corre localmente. El LLM es Ollama en tu máquina. `~/.keel/` nunca sale de tu equipo salvo que lo copies explícitamente. Usa `keel cifrar` para proteger los datos en reposo con AES-256-GCM y clave en el Keychain de macOS.

---

## Desarrollo

```bash
pip install -e ".[dev]"
make test           # pytest (excluye tests MCP lentos)
make test-all       # incluye tests MCP (~5 min)
make lint           # ruff
```
