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
  echo -e "  ${BOLD}${INFO}PRECIFICA${NC}  ${DIVIDER}│${NC}  ${ACCENT}${BOLD}SSH DEV TUNNEL${NC}  ${DIM}Desinstalador${NC}"
  echo -e "$DIV"
  [ -n "$1" ] && echo -e "  ${LABEL}ETAPA   ${NC}  ${ACCENT}$1${NC}\n$DIV"
}

ok()   { echo -e "  ${SUCCESS}✔  $1${NC}"; }
err()  { echo -e "  ${ERROR}✘  $1${NC}"; }
warn() { echo -e "  ${WARN}⚠  $1${NC}"; }
info() { echo -e "  ${DIM}$1${NC}"; }

# ─── Detectar Perfil do Shell ────────────────────────────────────
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bash_profile"; fi

# ─── Confirmação Inicial ─────────────────────────────────────────
header "Confirmação"
echo ""
warn "Esta ação removerá o atalho 'tunnel' do seu sistema."
echo -e "\n  ${LABEL}Perfil detectado:${NC}  ${ACCENT}$PROFILE${NC}\n"
echo -e "$DIV"
echo -e "  ${BOLD}${WARN}Deseja continuar? (s/N)${NC}  \c"
read -r confirm </dev/tty

if [[ ! "$confirm" =~ ^([sS])$ ]]; then
  echo -e "\n\n  ${DIM}Desinstalação cancelada.${NC}\n"
  exit 0
fi

# ─── Remover Alias ───────────────────────────────────────────────
header "Removendo Atalho"
echo ""

if [ -f "$PROFILE" ]; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/alias tunnel=/d' "$PROFILE" 2>/dev/null
  else
    sed -i.bak '/alias tunnel=/d' "$PROFILE" 2>/dev/null
  fi
  ok "Atalho 'tunnel' removido de $PROFILE"
else
  warn "Arquivo de perfil não encontrado: $PROFILE"
fi

# ─── Perguntar sobre Dados ───────────────────────────────────────
echo ""
echo -e "$DIV"
echo ""
warn "Deseja apagar também os servidores e chaves PEM salvos?"
echo -e "\n  ${DIM}~/.dev_tunnel_config/  e  ~/.dev_tunnel/${NC}\n"
echo -e "$DIV"
echo -e "  ${BOLD}${WARN}Apagar configurações? (s/N)${NC}  \c"
read -r response </dev/tty

if [[ "$response" =~ ^([sS])$ ]]; then
  echo ""
  rm -rf ~/.dev_tunnel_config
  rm -rf ~/.dev_tunnel
  ok "Configurações e chaves removidas."
else
  echo ""
  info "Configurações mantidas em ~/.dev_tunnel_config"
fi

# ─── Conclusão ───────────────────────────────────────────────────
echo ""
echo -e "$DIV"
echo -e "\n  ${BOLD}${INFO}CONCLUÍDO${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal para aplicar:"
echo -e "       ${ACCENT}source $PROFILE${NC}\n"
echo -e "$DIV\n"