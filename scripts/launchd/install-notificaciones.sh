#!/bin/bash
# Instala un launchd agent que ejecuta `keel agenda notificar` cada mañana a las 9am.

set -e

PLIST="$HOME/Library/LaunchAgents/com.keel.notificaciones.plist"
KEEL="$HOME/.local/bin/keel"

if [ ! -f "$KEEL" ]; then
  echo "keel no está instalado en $KEEL. Ejecuta install.sh primero."
  exit 1
fi

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.keel.notificaciones</string>
  <key>ProgramArguments</key>
  <array>
    <string>$KEEL</string>
    <string>agenda</string>
    <string>notificar</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>$HOME/.keel/logs/notificaciones.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.keel/logs/notificaciones-error.log</string>
</dict>
</plist>
EOF

mkdir -p "$HOME/.keel/logs"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "✓ Notificaciones diarias activadas (9:00 AM)"
echo "  Plist: $PLIST"
echo "  Log:   ~/.keel/logs/notificaciones.log"
echo ""
echo "Para desactivar: launchctl unload -w $PLIST"
