#!/usr/bin/env bash
# Instalador de keel-core
# Uso local:  bash install.sh
# Uso remoto: curl -fsSL https://raw.githubusercontent.com/juandcs/keel-core/main/install.sh | bash
set -euo pipefail

# ── Configuración ─────────────────────────────────────────────────────────────
KEEL_VERSION="0.1.0"
KEEL_APP_DIR="${HOME}/.local/share/keel-core"
KEEL_BIN_DIR="${HOME}/.local/bin"
KEEL_DATA_DIR="${HOME}/.keel"
GITHUB_REPO="juandcs/keel-core"

# ── Colores ───────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

# ── Helpers ───────────────────────────────────────────────────────────────────
banner()  { printf "\n${BOLD}  Keel — Motor de extensión cognitiva personal${NC}\n${BLUE}  v%s · local first · open source${NC}\n\n" "$KEEL_VERSION"; }
step()    { printf "${BOLD}→ %s${NC}\n" "$1"; }
ok()      { printf "${GREEN}  ✓ %s${NC}\n" "$1"; }
warn()    { printf "${YELLOW}  ⚠ %s${NC}\n" "$1"; }
fail()    { printf "${RED}  ✗ %s${NC}\n" "$1"; exit 1; }

# ── Paso 1: Python 3.11+ ─────────────────────────────────────────────────────
check_python() {
    step "Verificando Python 3.11+"
    PYTHON=""
    for cmd in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "$cmd" &>/dev/null; then
            IFS='.' read -r major minor _ < <("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.0')")
            if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
                PYTHON="$cmd"
                ok "Python ${major}.${minor} → $cmd"
                break
            fi
        fi
    done
    [ -n "$PYTHON" ] || fail "Python 3.11+ requerido. Descarga desde https://python.org"
}

# ── Paso 2: Ollama (advertencia, no falla) ────────────────────────────────────
check_ollama() {
    step "Verificando Ollama"
    if command -v ollama &>/dev/null; then
        ok "Ollama instalado"
    else
        warn "Ollama no encontrado — instala desde https://ollama.ai"
        warn "keel respond y keel mcp requieren Ollama para inferencia local."
    fi
}

# ── Paso 3: Obtener código fuente ─────────────────────────────────────────────
get_source() {
    step "Preparando código fuente"

    # Detectar si corremos desde el repo local (no piped desde curl)
    SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
    if [ -n "$SCRIPT_SOURCE" ] && [ "$SCRIPT_SOURCE" != "-" ]; then
        SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
        if [ -f "$SCRIPT_DIR/pyproject.toml" ] && grep -q "keel-core" "$SCRIPT_DIR/pyproject.toml" 2>/dev/null; then
            if [ "$SCRIPT_DIR" != "$KEEL_APP_DIR" ]; then
                mkdir -p "$KEEL_APP_DIR"
                rsync -a --exclude='.venv' --exclude='__pycache__' --exclude='*.egg-info' \
                      "$SCRIPT_DIR/" "$KEEL_APP_DIR/" 2>/dev/null || \
                cp -r "$SCRIPT_DIR/." "$KEEL_APP_DIR/"
                ok "Código copiado desde instalación local ($SCRIPT_DIR)"
            else
                ok "Ejecutando desde la ubicación de instalación"
            fi
            return
        fi
    fi

    # Si ya está instalado, actualizar
    if [ -d "$KEEL_APP_DIR/.git" ]; then
        cd "$KEEL_APP_DIR" && git pull --quiet --ff-only
        ok "Código actualizado desde GitHub"
        return
    fi

    # Clonar desde GitHub
    if command -v git &>/dev/null; then
        git clone --quiet "https://github.com/${GITHUB_REPO}.git" "$KEEL_APP_DIR"
        ok "Código descargado desde GitHub"
    else
        fail "git no encontrado. Instala git o ejecuta el instalador desde el repo local."
    fi
}

# ── Paso 4: Virtualenv e instalación ─────────────────────────────────────────
install_package() {
    step "Instalando keel-core"
    cd "$KEEL_APP_DIR"

    if [ ! -d ".venv" ]; then
        "$PYTHON" -m venv .venv --upgrade-deps 2>/dev/null || "$PYTHON" -m venv .venv
        ok "Entorno virtual creado"
    else
        ok "Entorno virtual existente reutilizado"
    fi

    .venv/bin/pip install -e . --quiet
    ok "Dependencias instaladas"
}

# ── Paso 5: Enlace del binario ────────────────────────────────────────────────
link_binary() {
    step "Enlazando comando keel"
    mkdir -p "$KEEL_BIN_DIR"
    ln -sf "$KEEL_APP_DIR/.venv/bin/keel" "$KEEL_BIN_DIR/keel"
    ok "keel → $KEEL_BIN_DIR/keel"
}

# ── Paso 6: PATH ──────────────────────────────────────────────────────────────
setup_path() {
    step "Configurando PATH"
    case "${SHELL:-}" in
        */zsh)  SHELL_CONFIG="${HOME}/.zshrc" ;;
        */bash) SHELL_CONFIG="${HOME}/.bashrc" ;;
        *)      SHELL_CONFIG="${HOME}/.profile" ;;
    esac

    if grep -q '.local/bin' "$SHELL_CONFIG" 2>/dev/null; then
        ok "PATH ya incluye ~/.local/bin ($SHELL_CONFIG)"
    else
        printf '\n# keel-core\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$SHELL_CONFIG"
        ok "PATH actualizado en $SHELL_CONFIG"
    fi

    export PATH="${KEEL_BIN_DIR}:${PATH}"
}

# ── Paso 7: Inicializar datos ─────────────────────────────────────────────────
initialize() {
    step "Inicializando ~/.keel/"
    "$KEEL_BIN_DIR/keel" init
}

# ── Paso 8: Verificar ─────────────────────────────────────────────────────────
verify() {
    step "Verificando instalación"
    "$KEEL_BIN_DIR/keel" status
}

# ── Main ──────────────────────────────────────────────────────────────────────
banner
check_python
check_ollama
get_source
install_package
link_binary
setup_path
initialize
verify

printf "\n${BOLD}${GREEN}  Keel instalado correctamente.${NC}\n\n"
printf "  Próximos pasos:\n"
printf "  1. Edita tu perfil:    ${BOLD}nano ~/.keel/perfil.json${NC}\n"
printf "  2. Agrega una persona: ${BOLD}keel persona add Nombre --rol 'rol'${NC}\n"
printf "  3. Primera respuesta:  ${BOLD}keel respond 'mensaje' --remitente Nombre${NC}\n"
printf "  4. Claude Code MCP:    ${BOLD}claude mcp add keel ~/.local/bin/keel mcp${NC}\n"
printf "\n  Documentación: ${BLUE}keel --help${NC}\n\n"

# Recordatorio de reload si se modificó el shell config
if [ "${PATH_UPDATED:-0}" = "1" ]; then
    printf "  ${YELLOW}Ejecuta: source ~/.zshrc  (o abre una nueva terminal)${NC}\n\n"
fi
