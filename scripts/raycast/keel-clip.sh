#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Keel - Responder mensaje
# @raycast.mode silent
# @raycast.packageName Keel
#
# Optional parameters:
# @raycast.icon 🧠
# @raycast.argument1 { "type": "text", "placeholder": "Remitente (vacío = picker)", "optional": true }
# @raycast.description Genera una sugerencia de respuesta al texto en el clipboard y lo copia de vuelta.

KEEL="$HOME/.local/bin/keel"

if [ ! -f "$KEEL" ]; then
  osascript -e 'display notification "keel no está instalado. Ejecuta install.sh" with title "Keel"'
  exit 1
fi

REMITENTE="$1"

if [ -n "$REMITENTE" ]; then
  "$KEEL" clip --remitente "$REMITENTE" --copiar --no-guardar
else
  # Sin remitente: abre Terminal con picker interactivo
  osascript <<'APPLESCRIPT'
    tell application "Terminal"
      activate
      do script "keel clip --copiar"
    end tell
APPLESCRIPT
fi
