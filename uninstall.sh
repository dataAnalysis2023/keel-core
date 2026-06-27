#!/usr/bin/env bash
# Desinstalador de keel-core
# Elimina la app pero preserva los datos del usuario (~/.keel/)
set -euo pipefail

KEEL_APP_DIR="${HOME}/.local/share/keel-core"
KEEL_BIN_DIR="${HOME}/.local/bin"
KEEL_DATA_DIR="${HOME}/.keel"

if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BOLD=''; NC=''
fi

printf "\n${BOLD}Desinstalando keel-core${NC}\n\n"
printf "${YELLOW}  ⚠ Esto elimina la app pero preserva tus datos en ~/.keel/${NC}\n\n"

# Ofrecer backup antes de continuar
if [ -d "$KEEL_DATA_DIR" ] && command -v "$KEEL_BIN_DIR/keel" &>/dev/null 2>&1; then
    read -rp "  ¿Hacer backup de ~/.keel/ antes de desinstalar? [S/n] " hacer_backup
    hacer_backup="${hacer_backup:-s}"
    if [[ "${hacer_backup,,}" != "n" ]]; then
        BACKUP_RUTA="${HOME}/keel-backup-$(date +%Y%m%d).zip"
        "$KEEL_BIN_DIR/keel" backup "$BACKUP_RUTA"
        printf "${GREEN}  ✓ Backup guardado en ${BACKUP_RUTA}${NC}\n\n"
    fi
fi

read -rp "  ¿Continuar con la desinstalación? [s/N] " respuesta
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
