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

ok()    { echo -e "  ${SUCCESS}✔  $1${NC}"; }
err()   { echo -e "  ${ERROR}✘  $1${NC}"; }
warn()  { echo -e "  ${WARN}⚠  $1${NC}"; }
info()  { echo -e "  ${DIM}$1${NC}"; }

# ─── Configurações ───────────────────────────────────────────────
REPO_URL="https://github.com/igor-rl/ssh_dev_tunnel.git"
IMAGE="ghcr.io/igor-rl/ssh_dev_tunnel:latest"

# Limpa buffer de input residual
while read -r -t 0; do read -r; done

# ─── Detectar Perfil do Shell ────────────────────────────────────
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bashrc"; fi # Alterado de .bash_profile para .bashrc (mais comum em WSL/Linux)
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
  info "Configurando atalho via Docker com suporte a múltiplas portas..."

  # Remove alias ou função anterior para evitar duplicidade
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    sed -i '' '/tunnel() {/,/}/d' "$PROFILE" 2>/dev/null
  else
    sed -i '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    sed -i '/tunnel() {/,/}/d' "$PROFILE" 2>/dev/null
  fi

  # Gera a função tunnel dinâmica
  {
    echo "tunnel() {"
    echo "  PORT=2222"
    echo "  if [[ \"\$1\" == \"--port\" && -n \"\$2\" ]]; then PORT=\$2; fi"
    echo "  if [ \"\$(pwd)\" = \"\$HOME\" ]; then"
    echo "    echo -e \"\\n  ${ERROR}Erro:${NC} Entre em uma pasta de projeto antes de rodar o tunnel.\\n\""
    echo "  else"
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
      echo "    winpty docker run -it --rm --pull always -p \$PORT:\$PORT \\"
      echo "      -v ~/.dev_tunnel_config:/root/.dev_tunnel \\"
      echo "      -v \"\$(cygpath -m \"\$(pwd)\"):/app\" \\"
      echo "      -e HOST_PROJECT_PATH=\"\$(cygpath -m \"\$(pwd)\")\" \\"
      echo "      $IMAGE python3 /app/main.py --port \$PORT"
    else
      echo "    docker run -it --rm --pull always -p \$PORT:\$PORT \\"
      echo "      -v ~/.dev_tunnel_config:/root/.dev_tunnel \\"
      echo "      -v \"\$(pwd):/app\" \\"
      echo "      -e HOST_PROJECT_PATH=\"\$(pwd)\" \\"
      echo "      $IMAGE python3 /app/main.py --port \$PORT"
    fi
    echo "  fi"
    echo "}"
  } >> "$PROFILE"

  ok "Função 'tunnel' adicionada em $PROFILE"

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
echo -e "  ${LABEL}2.${NC}  Uso padrão (Porta 2222):"
echo -e "       ${ACCENT}tunnel${NC}\n"
echo -e "  ${LABEL}3.${NC}  Uso múltiplo (Outra porta):"
echo -e "       ${ACCENT}tunnel --port 2223${NC}\n"
echo -e "$DIV\n"