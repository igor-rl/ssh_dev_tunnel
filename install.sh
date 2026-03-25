#!/bin/bash

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

# ─── Layout ──────────────────────────────────────────────────────
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

# ─── Configurações ───────────────────────────────────────────────
REPO_URL="https://github.com/igor-rl/ssh_dev_tunnel.git"
IMAGE="ghcr.io/igor-rl/ssh_dev_tunnel:latest"

# Limpa buffer de input residual
while read -r -t 0; do read -r; done

# ─── Detectar Perfil do Shell ────────────────────────────────────
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bash_profile"; fi
touch "$PROFILE"

# ─── Detectar Dependências ───────────────────────────────────────
HAS_DOCKER=false
HAS_PYTHON=false
command -v docker  &>/dev/null && HAS_DOCKER=true
command -v python3 &>/dev/null && HAS_PYTHON=true

# ─── Montar Opções ───────────────────────────────────────────────
options=()
[ "$HAS_DOCKER" = true ] && options+=("Docker  ${DIM}(Recomendado — isolado, sem dependências)${NC}")
[ "$HAS_PYTHON" = true ] && options+=("Python  ${DIM}(Local — requer sshpass instalado)${NC}")
options+=("Sair")

# ─── Menu Interativo ─────────────────────────────────────────────
selected=0

draw_menu() {
  header "Método de Instalação"
  echo -e "  ${BOLD}${INFO}Como deseja instalar a ferramenta?${NC}\n"
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

# ─── Executar Escolha ────────────────────────────────────────────
if [[ "$CHOICE" == *"Docker"* ]]; then

  header "Docker"
  echo ""
  info "Configurando atalho via Docker..."

  # Remove alias anterior
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/alias tunnel=/d' "$PROFILE" 2>/dev/null
  else
    sed -i '/alias tunnel=/d' "$PROFILE" 2>/dev/null
  fi

  # Gera o alias correto por SO
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    CMD="alias tunnel='winpty docker run -it --rm --pull always -p 2222:2222 -v ~/.dev_tunnel_config:/root/.dev_tunnel -v \"\$(cygpath -m \"\$(pwd)\"):/app\" -e HOST_PROJECT_PATH=\"\$(cygpath -m \"\$(pwd)\")\" $IMAGE'"
  else
    CMD="alias tunnel='docker run -it --rm --pull always -p 2222:2222 -v ~/.dev_tunnel_config:/root/.dev_tunnel -v \"\$(pwd):/app\" -e HOST_PROJECT_PATH=\"\$(pwd)\" $IMAGE'"
  fi

  echo "$CMD" >> "$PROFILE"
  ok "Atalho Docker adicionado em $PROFILE"

elif [[ "$CHOICE" == *"Python"* ]]; then

  header "Python Local"
  echo ""
  info "Instalando pacote via pip..."

  PIP_CMD=$(command -v pip3 || command -v pip)
  $PIP_CMD install --upgrade --user "git+$REPO_URL"

  BIN_PATH=$(python3 -m site --user-base)/bin
  if [[ ":$PATH:" != *":$BIN_PATH:"* ]]; then
    echo "export PATH=\"\$PATH:$BIN_PATH\"" >> "$PROFILE"
    info "PATH atualizado em $PROFILE"
  fi

  ok "Instalação local concluída."

else
  echo -e "\n  ${DIM}Instalação cancelada.${NC}\n"
  exit 0
fi

# ─── Instruções Finais ───────────────────────────────────────────
echo -e "\n$DIV"
echo -e "\n  ${BOLD}${INFO}PRÓXIMOS PASSOS${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal:"
echo -e "       ${ACCENT}source $PROFILE${NC}\n"
echo -e "  ${LABEL}2.${NC}  Inicie a ferramenta em qualquer projeto:"
echo -e "       ${ACCENT}tunnel${NC}\n"
echo -e "$DIV\n"