#!/bin/bash
set -e

# ─── Paleta ─────────────────────────────────────────────────────
ACCENT='\033[38;5;75m'
SUCCESS='\033[38;5;114m'
WARN='\033[38;5;178m'
ERROR='\033[38;5;196m'
DIM='\033[38;5;240m'
LABEL='\033[38;5;244m'
INFO='\033[38;5;252m'
DIVIDER='\033[38;5;238m'
NC='\033[0m'
BOLD='\033[1m'

W="─────────────────────────────────────────────────────────────────"
DIV="${DIVIDER}${W}${NC}"

header() {
  clear
  echo -e "$DIV"
  echo -e "  ${BOLD}${INFO}PRECIFICA${NC}  ${DIVIDER}│${NC}  ${ACCENT}${BOLD}SSH DEV TUNNEL${NC}  ${DIM}Instalador${NC}"
  echo -e "$DIV"
  [ -n "$1" ] && echo -e "  ${LABEL}ETAPA   ${NC}  ${ACCENT}$1${NC}\n$DIV"
}

ok()   { echo -e "  ${SUCCESS}✔  $1${NC}"; }
err()  { echo -e "  ${ERROR}✘  $1${NC}"; }
warn() { echo -e "  ${WARN}⚠  $1${NC}"; }
info() { echo -e "  ${DIM}$1${NC}"; }

REPO_URL="https://github.com/igor-rl/ssh_dev_tunnel.git"

# ─── Limpa buffer de stdin ───────────────────────────────────────
while read -r -t 0; do read -r; done

# ─── Remove atalho/função Docker de instalações antigas (< v3.9.0) ──
SENTINEL_BEGIN="# >>> ssh_dev_tunnel begin <<<"
SENTINEL_END="# >>> ssh_dev_tunnel end <<<"

remove_legacy_docker_shortcut() {
  local profile="$1"
  [ -f "$profile" ] || return
  local changed=false

  if grep -qF "$SENTINEL_BEGIN" "$profile" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    else
      sed -i "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    fi
    changed=true
  fi

  if grep -q 'alias tunnel=' "$profile" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' '/alias tunnel=/d' "$profile"
    else
      sed -i '/alias tunnel=/d' "$profile"
    fi
    changed=true
  fi

  if [ "$changed" = true ]; then
    ok "Atalho Docker legado removido de $(basename "$profile")"
  fi
}

for prof in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
  remove_legacy_docker_shortcut "$prof"
done

# ─── Localiza um Python 3.10+ ────────────────────────────────────
find_python() {
  for candidate in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
      if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

# ─── Menu ────────────────────────────────────────────────────────
options=("Instalar" "Desinstalar" "Sair")
selected=0

draw_menu() {
  header "Método de Instalação"
  echo -e "  ${BOLD}${INFO}O que deseja fazer?${NC}\n"
  for i in "${!options[@]}"; do
    if [ "$i" -eq "$selected" ]; then
      echo -e "  ${ACCENT}▶  ${BOLD}${options[$i]}${NC}"
    else
      echo -e "     ${DIM}${options[$i]}${NC}"
    fi
  done
  echo -e "\n$DIV"
  echo -e "  ${DIM}↑ ↓  navegar    ENTER  confirmar    Q  sair${NC}"
}

while true; do
  draw_menu
  read -rsn3 key </dev/tty
  case "$key" in
    $'\x1b\x5b\x41') ((selected--)); [ $selected -lt 0 ] && selected=$((${#options[@]} - 1)) ;;
    $'\x1b\x5b\x42') ((selected++)); [ $selected -ge ${#options[@]} ] && selected=0 ;;
    "" | $'\x0a')  break ;;
    "q" | "Q")     echo -e "\n  ${DIM}Instalação cancelada.${NC}\n"; exit 0 ;;
  esac
done

CHOICE="${options[$selected]}"

# ════════════════════════════════════════════════════════════════
if [[ "$CHOICE" == "Instalar" ]]; then

  header "Pré-requisitos"
  echo ""

  PYTHON_BIN=$(find_python) || {
    err "Python 3.10+ não encontrado."
    echo ""
    info "Instale o Python 3.10 ou superior antes de continuar:"
    info "  macOS:   brew install python@3.12"
    info "  Linux:   sudo apt install python3.12"
    info "  Windows: https://www.python.org/downloads/"
    echo ""
    exit 1
  }
  ok "Python detectado: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"

  if ! command -v sshpass &>/dev/null; then
    err "sshpass não encontrado."
    echo ""
    info "Instale o sshpass antes de continuar:"
    info "  macOS:   brew install hudochenkov/sshpass/sshpass"
    info "  Linux:   sudo apt install sshpass"
    info "  Windows: use WSL com sshpass instalado"
    echo ""
    exit 1
  fi
  ok "sshpass encontrado."

  echo ""
  info "Seus servidores, chaves PEM e senhas serão salvos em: ~/.dev_tunnel/"
  info "Persistem entre atualizações e reinstalações."
  echo ""

  header "Instalando"
  echo ""

  if command -v pipx &>/dev/null; then
    ok "pipx encontrado — instalando de forma isolada."
    pipx install --force "git+${REPO_URL}"
    pipx ensurepath
  else
    warn "pipx não encontrado — recomendado para evitar conflitos com outros pacotes Python."
    info "  Instale com: brew install pipx   (ou) sudo apt install pipx"
    echo ""
    echo -e "  ${WARN}Instalar mesmo assim via pip --user? (s/N)${NC}  \c"
    read -r resp </dev/tty
    if [[ ! "$resp" =~ ^([sS])$ ]]; then
      echo -e "\n  ${DIM}Instalação cancelada. Instale o pipx e rode este script de novo.${NC}\n"
      exit 0
    fi
    "$PYTHON_BIN" -m pip install --user --upgrade "git+${REPO_URL}" \
      || "$PYTHON_BIN" -m pip install --user --break-system-packages --upgrade "git+${REPO_URL}"
  fi

  echo ""
  ok "ssh-dev-tunnel instalado."

# ════════════════════════════════════════════════════════════════
elif [[ "$CHOICE" == "Desinstalar" ]]; then

  header "Desinstalação"
  echo ""

  if command -v pipx &>/dev/null && pipx list --short 2>/dev/null | grep -q "^ssh-dev-tunnel "; then
    pipx uninstall ssh-dev-tunnel && ok "Pacote removido via pipx."
  elif command -v pip3 &>/dev/null; then
    pip3 uninstall -y ssh-dev-tunnel 2>/dev/null \
      && ok "Pacote removido via pip." \
      || info "Pacote não encontrado (já removido?)."
  fi

  echo ""
  warn "Deseja apagar também os dados salvos? (~/.dev_tunnel)"
  echo -e "  ${DIM}Contém: servidores, chaves PEM e vault de senhas${NC}\n"
  echo -e "$DIV"
  echo -e "  ${BOLD}${WARN}Apagar dados? (s/N)${NC}  \c"
  read -r response </dev/tty
  if [[ "$response" =~ ^([sS])$ ]]; then
    rm -rf "$HOME/.dev_tunnel"
    ok "Diretório ~/.dev_tunnel removido."
  else
    info "Dados mantidos em ~/.dev_tunnel"
  fi

  echo ""
  exit 0

else
  echo -e "\n  ${DIM}Cancelado.${NC}\n"
  exit 0
fi

# ─── Instruções Finais ───────────────────────────────────────────
echo -e "\n$DIV"
echo -e "\n  ${BOLD}${INFO}PRÓXIMOS PASSOS${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal (ou abra um novo):"
echo -e "       ${ACCENT}exec \$SHELL${NC}\n"
echo -e "  ${LABEL}2.${NC}  Uso padrão (porta 2222 ou próxima livre):"
echo -e "       ${ACCENT}tunnel${NC}\n"
echo -e "  ${LABEL}3.${NC}  Especificar porta:"
echo -e "       ${ACCENT}tunnel --port 2223${NC}"
echo -e "       ${ACCENT}tunnel -p 2224${NC}\n"
echo -e "  ${WARN}⚠ Certifique-se de instalar a extensão SSH FS no Cursor/Code.${NC}"
echo -e "$DIV\n"
