#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Keel - Conversar
# @raycast.mode silent
# @raycast.packageName Keel
#
# Optional parameters:
# @raycast.icon 💬
# @raycast.argument1 { "type": "text", "placeholder": "Remitente (vacío = picker)", "optional": true }
# @raycast.description Abre el flujo completo de conversación en Terminal.

REMITENTE="$1"

if [ -n "$REMITENTE" ]; then
  CMD="keel conversar --remitente '$REMITENTE'"
else
  CMD="keel conversar"
fi

osascript <<APPLESCRIPT
  tell application "Terminal"
    activate
    do script "$CMD"
  end tell
APPLESCRIPT
