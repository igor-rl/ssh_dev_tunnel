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

# ─── Limpa buffer de input residual ──────────────────────────────
while read -r -t 0; do read -r; done

# ─── Detectar Perfil do Shell ────────────────────────────────────
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bashrc"; fi
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
options+=("Desinstalar")
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

# ════════════════════════════════════════════════════════════════
# ─── Função de limpeza robusta do profile ───────────────────────
# Marca o bloco com comentários sentinela para remoção precisa.
# ════════════════════════════════════════════════════════════════
SENTINEL_BEGIN="# >>> ssh_dev_tunnel begin <<<"
SENTINEL_END="# >>> ssh_dev_tunnel end <<<"

remove_tunnel_block() {
  local profile="$1"
  if grep -q "$SENTINEL_BEGIN" "$profile" 2>/dev/null; then
    # Remove o bloco entre as sentinelas (inclusive) em qualquer OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    else
      sed -i "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    fi
    ok "Bloco 'tunnel' removido de $profile"
  else
    # Fallback: tenta remover vestígios antigos sem sentinelas
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' '/^tunnel() {/,/^}/d' "$profile" 2>/dev/null
      sed -i '' '/^alias tunnel=/d'   "$profile" 2>/dev/null
    else
      sed -i '/^tunnel() {/,/^}/d' "$profile" 2>/dev/null
      sed -i '/^alias tunnel=/d'   "$profile" 2>/dev/null
    fi
    warn "Sentinelas não encontradas — tentativa de limpeza manual aplicada."
  fi
}

write_tunnel_block() {
  local profile="$1"
  # Remove bloco anterior antes de reescrever
  remove_tunnel_block "$profile"

  cat >> "$profile" << 'SHELLBLOCK'
# >>> ssh_dev_tunnel begin <<<
tunnel() {
  local PORT=2222
  # Suporta: tunnel, tunnel --port 2223, tunnel -p 2223
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port|-p) PORT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done

  if [ "$(pwd)" = "$HOME" ]; then
    echo -e "\n  \033[38;5;196mErro:\033[0m Entre em uma pasta de projeto antes de rodar o tunnel.\n"
    return 1
  fi

SHELLBLOCK

  # A parte com variáveis do shell do instalador (não heredoc literal)
  {
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
      cat >> "$profile" << 'SHELLBLOCK'
  winpty docker run -it --rm --pull always \
    -p "${PORT}:${PORT}" \
    -v ~/.dev_tunnel_config:/home/tunnel/.dev_tunnel \
    -e HOST_PROJECT_PATH="$(cygpath -m "$(pwd)")" \
    ghcr.io/igor-rl/ssh_dev_tunnel:latest --port "$PORT"
SHELLBLOCK
    else
      cat >> "$profile" << 'SHELLBLOCK'
  docker run -it --rm --pull always \
    -p "${PORT}:${PORT}" \
    -v ~/.dev_tunnel_config:/home/tunnel/.dev_tunnel \
    -e HOST_PROJECT_PATH="$(pwd)" \
    ghcr.io/igor-rl/ssh_dev_tunnel:latest --port "$PORT"
SHELLBLOCK
    fi
  }

  cat >> "$profile" << 'SHELLBLOCK'
}
# >>> ssh_dev_tunnel end <<<
SHELLBLOCK
}

# ════════════════════════════════════════════════════════════════
# ─── Docker ─────────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════
if [[ "$CHOICE" == *"Docker"* ]]; then

  header "Docker"
  echo ""
  info "Configurando atalho via Docker com suporte a múltiplas portas..."

  write_tunnel_block "$PROFILE"
  ok "Função 'tunnel' adicionada em $PROFILE"

# ════════════════════════════════════════════════════════════════
# ─── Python Local ───────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════
elif [[ "$CHOICE" == *"Python"* ]]; then

  header "Python Local"
  echo ""
  info "Instalando pacote via pip..."

  PIP_CMD=$(command -v pip3 || command -v pip)
  $PIP_CMD install --upgrade --user "git+$REPO_URL"

  BIN_PATH=$(python3 -m site --user-base)/bin
  if [[ ":$PATH:" != *":$BIN_PATH:"* ]]; then
    {
      echo "$SENTINEL_BEGIN"
      echo "export PATH=\"\$PATH:$BIN_PATH\""
      echo "$SENTINEL_END"
    } >> "$PROFILE"
    info "PATH atualizado em $PROFILE"
  fi

  ok "Instalação local concluída."

# ════════════════════════════════════════════════════════════════
# ─── Desinstalar ────────────────────────────────────────────────
# ════════════════════════════════════════════════════════════════
elif [[ "$CHOICE" == *"Desinstalar"* ]]; then

  header "Desinstalação"
  echo ""

  # Remove bloco do profile ativo
  remove_tunnel_block "$PROFILE"

  # Garante limpeza em ambos os profiles caso o usuário tenha trocado de shell
  for alt in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    [ "$alt" != "$PROFILE" ] && [ -f "$alt" ] && remove_tunnel_block "$alt"
  done

  # Remove pip local (Python)
  if command -v pip3 &>/dev/null; then
    pip3 uninstall -y ssh-dev-tunnel 2>/dev/null \
      && ok "Pacote Python removido." \
      || info "Pacote Python não encontrado via pip."
  fi

  # Remove dados locais (cofre, chaves, workspaces)
  CONFIG_BASE="$HOME/.dev_tunnel_config"
  if [ -d "$CONFIG_BASE" ]; then
    rm -rf "$CONFIG_BASE"
    ok "Diretório $CONFIG_BASE removido."
  fi

  echo ""
  warn "Recarregue o terminal para que 'tunnel' deixe de funcionar:"
  echo -e "       ${ACCENT}exec \$SHELL${NC}\n"
  exit 0

# ════════════════════════════════════════════════════════════════
else
  echo -e "\n  ${DIM}Instalação cancelada.${NC}\n"
  exit 0
fi

# ─── Instruções Finais ───────────────────────────────────────────
echo -e "\n$DIV"
echo -e "\n  ${BOLD}${INFO}PRÓXIMOS PASSOS${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal:"
echo -e "       ${ACCENT}source $PROFILE${NC}\n"
echo -e "  ${LABEL}2.${NC}  Uso padrão (porta 2222 ou próxima livre):"
echo -e "       ${ACCENT}tunnel${NC}\n"
echo -e "  ${LABEL}3.${NC}  Especificar porta (próxima livre se ocupada):"
echo -e "       ${ACCENT}tunnel --port 2223${NC}"
echo -e "       ${ACCENT}tunnel -p 2224${NC}\n"
echo -e "  ${WARN}⚠ Certifique-se de instalar a extensão SSH FS no Cursor/Code.${NC}"
echo -e "$DIV\n"