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

# ─── Confirmação Inicial ─────────────────────────────────────────
header "Confirmação"
echo ""
warn "Esta ação removerá o pacote 'ssh-dev-tunnel' do seu sistema."
echo -e "$DIV"
echo -e "  ${BOLD}${WARN}Deseja continuar? (s/N)${NC}  \c"
read -r confirm </dev/tty
if [[ ! "$confirm" =~ ^([sS])$ ]]; then
  echo -e "\n\n  ${DIM}Desinstalação cancelada.${NC}\n"
  exit 0
fi

# ─── Remover instalação (pipx ou pip) ─────────────────────────────
header "Removendo Pacote"
echo ""

if command -v pipx &>/dev/null && pipx list --short 2>/dev/null | grep -q "^ssh-dev-tunnel "; then
  pipx uninstall ssh-dev-tunnel && ok "Pacote removido via pipx."
elif command -v pip3 &>/dev/null; then
  pip3 uninstall -y ssh-dev-tunnel 2>/dev/null \
    && ok "Pacote removido via pip." \
    || info "Pacote não encontrado (já removido?)."
else
  info "pip/pipx não encontrado — nada para remover."
fi

# ─── Perguntar sobre Dados ───────────────────────────────────────
echo ""
echo -e "$DIV"
echo ""
warn "Deseja apagar também os servidores e chaves PEM salvos?"
echo -e "\n  ${DIM}Contém: servidores, chaves PEM e vault de senhas${NC}"
echo -e "  ${DIM}~/.dev_tunnel/${NC}\n"
echo -e "$DIV"
echo -e "  ${BOLD}${WARN}Apagar configurações? (s/N)${NC}  \c"
read -r response </dev/tty

if [[ "$response" =~ ^([sS])$ ]]; then
  echo ""
  rm -rf "$HOME/.dev_tunnel"
  ok "Configurações e chaves removidas."
else
  echo ""
  info "Dados mantidos em ~/.dev_tunnel"
fi

# ─── Conclusão ───────────────────────────────────────────────────
echo ""
echo -e "$DIV"
echo -e "\n  ${BOLD}${INFO}CONCLUÍDO${NC}\n"
echo -e "  ${LABEL}O comando 'tunnel' não deve mais funcionar.${NC}"
echo -e "$DIV\n"
