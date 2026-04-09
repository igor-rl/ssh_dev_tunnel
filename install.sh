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

IMAGE="ghcr.io/igor-rl/ssh_dev_tunnel:latest"
VOLUME_NAME="ssh_dev_tunnel_data"

# ─── Limpa buffer de stdin ───────────────────────────────────────
while read -r -t 0; do read -r; done

# ─── Verifica Docker obrigatório ─────────────────────────────────
if ! command -v docker &>/dev/null; then
  header "Erro"
  echo ""
  err "Docker não encontrado."
  echo ""
  info "Instale o Docker Desktop antes de continuar:"
  info "  https://www.docker.com/products/docker-desktop"
  echo ""
  exit 1
fi

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

# ─── Sentinelas ──────────────────────────────────────────────────
SENTINEL_BEGIN="# >>> ssh_dev_tunnel begin <<<"
SENTINEL_END="# >>> ssh_dev_tunnel end <<<"

remove_tunnel_block() {
  local profile="$1"
  [ -f "$profile" ] || return
  if grep -qF "$SENTINEL_BEGIN" "$profile" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    else
      sed -i "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    fi
    ok "Bloco anterior removido de $(basename "$profile")"
  else
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' '/alias tunnel=/d' "$profile" 2>/dev/null
    else
      sed -i '/alias tunnel=/d' "$profile" 2>/dev/null
    fi
    python3 - "$profile" <<'PYEOF' 2>/dev/null
import sys, re
path = sys.argv[1]
with open(path, 'r') as f: content = f.read()
cleaned = re.sub(r'\ntunnel\(\) \{[^}]*\}', '', content, flags=re.DOTALL)
with open(path, 'w') as f: f.write(cleaned)
PYEOF
  fi
}

# ─── Bloco da função tunnel a ser injetado nos profiles ──────────
# Usa volume Docker nomeado para persistência sem depender de dir local.
build_tunnel_block_unix() {
  cat << 'SHELLBLOCK'
# >>> ssh_dev_tunnel begin <<<
tunnel() {
  local PORT=2222
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port|-p) PORT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  docker run -it --rm --pull always \
    -p "${PORT}:${PORT}" \
    -v ssh_dev_tunnel_data:/home/tunnel/.dev_tunnel \
    -e HOST_PROJECT_PATH="/home/tunnel/.dev_tunnel" \
    ghcr.io/igor-rl/ssh_dev_tunnel:latest --port "$PORT"
}
# >>> ssh_dev_tunnel end <<<
SHELLBLOCK
}

build_tunnel_block_windows() {
  cat << 'SHELLBLOCK'
# >>> ssh_dev_tunnel begin <<<
tunnel() {
  local PORT=2222
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --port|-p) PORT="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  winpty docker run -it --rm --pull always \
    -p "${PORT}:${PORT}" \
    -v ssh_dev_tunnel_data:/home/tunnel/.dev_tunnel \
    -e HOST_PROJECT_PATH="/home/tunnel/.dev_tunnel" \
    ghcr.io/igor-rl/ssh_dev_tunnel:latest --port "$PORT"
}
# >>> ssh_dev_tunnel end <<<
SHELLBLOCK
}

# ─── Escreve o bloco em um profile, criando-o se necessário ──────
inject_into_profile() {
  local profile="$1"
  touch "$profile"
  remove_tunnel_block "$profile"
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    build_tunnel_block_windows >> "$profile"
  else
    build_tunnel_block_unix >> "$profile"
  fi
  ok "Função 'tunnel' adicionada em $profile"
}

# ════════════════════════════════════════════════════════════════
if [[ "$CHOICE" == "Instalar" ]]; then

  header "Docker"
  echo ""
  info "Usando volume Docker nomeado: ${VOLUME_NAME}"
  info "Os dados persistem mesmo após 'docker rm'."
  echo ""

  # Cria o volume nomeado caso não exista
  if ! docker volume inspect "$VOLUME_NAME" &>/dev/null; then
    docker volume create "$VOLUME_NAME" > /dev/null
    ok "Volume Docker '${VOLUME_NAME}' criado."
  else
    ok "Volume Docker '${VOLUME_NAME}' já existe."
  fi

  # Injeta em todos os profiles de shell encontrados
  PROFILES_WRITTEN=0

  # .bashrc — presente em Linux e WSL
  if [ -f "$HOME/.bashrc" ] || command -v bash &>/dev/null; then
    inject_into_profile "$HOME/.bashrc"
    PROFILES_WRITTEN=$((PROFILES_WRITTEN + 1))
  fi

  # .zshrc — presente em Mac e WSL com zsh (ex: Oh My Zsh no Windows)
  if [ -f "$HOME/.zshrc" ] || command -v zsh &>/dev/null; then
    inject_into_profile "$HOME/.zshrc"
    PROFILES_WRITTEN=$((PROFILES_WRITTEN + 1))
  fi

  # .bash_profile — fallback para Mac sem .bashrc
  if [[ "$OSTYPE" == "darwin"* ]] && [ ! -f "$HOME/.bashrc" ]; then
    inject_into_profile "$HOME/.bash_profile"
    PROFILES_WRITTEN=$((PROFILES_WRITTEN + 1))
  fi

  if [ "$PROFILES_WRITTEN" -eq 0 ]; then
    warn "Nenhum profile de shell detectado. Adicionando em ~/.bashrc como fallback."
    inject_into_profile "$HOME/.bashrc"
  fi

# ════════════════════════════════════════════════════════════════
elif [[ "$CHOICE" == "Desinstalar" ]]; then

  header "Desinstalação"
  echo ""

  for prof in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
    remove_tunnel_block "$prof"
  done

  echo ""
  warn "Deseja apagar também o volume Docker com servidores e chaves PEM?"
  echo -e "  ${DIM}Volume: ${VOLUME_NAME}${NC}\n"
  echo -e "$DIV"
  echo -e "  ${BOLD}${WARN}Apagar volume? (s/N)${NC}  \c"
  read -r response </dev/tty
  if [[ "$response" =~ ^([sS])$ ]]; then
    docker volume rm "$VOLUME_NAME" 2>/dev/null \
      && ok "Volume '${VOLUME_NAME}' removido." \
      || warn "Volume não encontrado ou já removido."
  else
    info "Volume mantido: ${VOLUME_NAME}"
  fi

  echo ""
  warn "Recarregue o terminal:"
  echo -e "       ${ACCENT}exec \$SHELL${NC}\n"
  exit 0

else
  echo -e "\n  ${DIM}Cancelado.${NC}\n"
  exit 0
fi

# ─── Instruções Finais ───────────────────────────────────────────
echo -e "\n$DIV"
echo -e "\n  ${BOLD}${INFO}PRÓXIMOS PASSOS${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal (em cada shell ativo):"
echo -e "       ${ACCENT}source ~/.bashrc${NC}   ${DIM}# bash / WSL${NC}"
echo -e "       ${ACCENT}source ~/.zshrc${NC}    ${DIM}# zsh${NC}\n"
echo -e "  ${LABEL}2.${NC}  Uso padrão (porta 2222 ou próxima livre):"
echo -e "       ${ACCENT}tunnel${NC}\n"
echo -e "  ${LABEL}3.${NC}  Especificar porta:"
echo -e "       ${ACCENT}tunnel --port 2223${NC}"
echo -e "       ${ACCENT}tunnel -p 2224${NC}\n"
echo -e "  ${WARN}⚠ Certifique-se de instalar a extensão SSH FS no Cursor/Code.${NC}"
echo -e "$DIV\n"