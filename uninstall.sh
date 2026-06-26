#!/usr/bin/env bash
# Desinstalador de keel-core
# Elimina la app pero preserva los datos del usuario (~/.keel/)
set -euo pipefail

KEEL_APP_DIR="${HOME}/.local/share/keel-core"
KEEL_BIN_DIR="${HOME}/.local/bin"

if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BOLD=''; NC=''
fi

printf "\n${BOLD}Desinstalando keel-core${NC}\n\n"
printf "${YELLOW}  ⚠ Esto elimina la app pero preserva tus datos en ~/.keel/${NC}\n\n"

read -rp "  ¿Continuar? [s/N] " respuesta
[ "${respuesta,,}" = "s" ] || { printf "  Cancelado.\n\n"; exit 0; }

echo ""

# Eliminar binario
if [ -L "$KEEL_BIN_DIR/keel" ]; then
    rm "$KEEL_BIN_DIR/keel"
    printf "${GREEN}  ✓ Binario eliminado${NC}\n"
fi

# Eliminar app
if [ -d "$KEEL_APP_DIR" ]; then
    rm -rf "$KEEL_APP_DIR"
    printf "${GREEN}  ✓ Aplicación eliminada ($KEEL_APP_DIR)${NC}\n"
fi

printf "\n  ${YELLOW}Tus datos en ~/.keel/ no fueron tocados.${NC}\n"
printf "  Para eliminarlos también: ${BOLD}rm -rf ~/.keel/${NC}\n\n"
printf "  Para reinstalar: ${BOLD}bash install.sh${NC}\n\n"
