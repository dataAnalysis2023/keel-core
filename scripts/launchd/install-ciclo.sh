#!/bin/bash
# Instala un launchd agent que ejecuta `keel ciclo` cada noche a las 2:00 AM.
# El ciclo sintetiza narrativas relacionales de todas las personas con historial.

set -e

PLIST="$HOME/Library/LaunchAgents/com.keel.ciclo.plist"
KEEL="$HOME/.local/bin/keel"
HORA=${1:-2}   # Hora de ejecución (default: 2am). Pasa otro valor como argumento.

if [ ! -f "$KEEL" ]; then
  echo "keel no está instalado en $KEEL. Ejecuta install.sh primero."
  exit 1
fi

mkdir -p "$HOME/.keel/logs"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.keel.ciclo</string>
  <key>ProgramArguments</key>
  <array>
    <string>$KEEL</string>
    <string>ciclo</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$HORA</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$HOME/.keel/logs/ciclo.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.keel/logs/ciclo-error.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:$HOME/.local/bin</string>
  </dict>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "✓ Ciclo nocturno activado (${HORA}:00 AM diario)"
echo "  Plist: $PLIST"
echo "  Log:   ~/.keel/logs/ciclo.log"
echo ""
echo "Para ver el log:      keel ciclo --ver-log"
echo "Para ejecutar ahora:  keel ciclo"
echo "Para desactivar:      launchctl unload -w $PLIST"
