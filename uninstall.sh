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

# ─── Sentinelas (devem ser idênticas às do install.sh) ──────────
SENTINEL_BEGIN="# >>> ssh_dev_tunnel begin <<<"
SENTINEL_END="# >>> ssh_dev_tunnel end <<<"

# ─── Remove o bloco sentinelado de um profile ───────────────────
# Também faz fallback para remoções legadas (sem sentinelas).
remove_tunnel_block() {
  local profile="$1"
  [ -f "$profile" ] || return

  if grep -qF "$SENTINEL_BEGIN" "$profile" 2>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    else
      sed -i.bak "/$SENTINEL_BEGIN/,/$SENTINEL_END/d" "$profile"
    fi
    ok "Bloco 'tunnel' removido de $profile"
  else
    # Fallback: instalações antigas sem sentinelas
    local changed=false
    if grep -q 'alias tunnel=' "$profile" 2>/dev/null; then
      if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/alias tunnel=/d' "$profile"
      else
        sed -i.bak '/alias tunnel=/d' "$profile"
      fi
      changed=true
    fi
    # Remove bloco tunnel() { ... } — sed lida mal com funções multilinhas;
    # usamos Python como ferramenta portável para isso.
    if grep -q 'tunnel() {' "$profile" 2>/dev/null; then
      python3 - "$profile" <<'PYEOF'
import sys, re
path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()
# Remove qualquer bloco: tunnel() { \n ... \n }
cleaned = re.sub(r'\ntunnel\(\) \{[^}]*\}', '', content, flags=re.DOTALL)
with open(path, 'w') as f:
    f.write(cleaned)
PYEOF
      changed=true
    fi
    if $changed; then
      warn "Sentinelas não encontradas — limpeza legada aplicada em $profile"
    else
      info "Nenhum atalho 'tunnel' encontrado em $profile"
    fi
  fi
}

# ─── Detectar Perfil Principal ───────────────────────────────────
if [ -n "$ZSH_VERSION" ]; then
  PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
  PROFILE="$HOME/.bashrc"
else
  PROFILE="$HOME/.bash_profile"
fi

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

# ─── Remover de todos os profiles conhecidos ─────────────────────
header "Removendo Atalho"
echo ""

for prof in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
  remove_tunnel_block "$prof"
done

# ─── Remover instalação pip (modo Python) ────────────────────────
echo ""
if command -v pip3 &>/dev/null; then
  pip3 uninstall -y ssh-dev-tunnel 2>/dev/null \
    && ok "Pacote Python 'ssh-dev-tunnel' removido via pip." \
    || info "Pacote pip não encontrado (modo Docker ou já removido)."
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
  # Remove também o diretório legado (~/.dev_tunnel_config) caso ainda exista
  rm -rf "$HOME/.dev_tunnel" "$HOME/.dev_tunnel_config"
  ok "Configurações e chaves removidas."
else
  echo ""
  info "Dados mantidos em ~/.dev_tunnel"
fi

# ─── Conclusão ───────────────────────────────────────────────────
echo ""
echo -e "$DIV"
echo -e "\n  ${BOLD}${INFO}CONCLUÍDO${NC}\n"
echo -e "  ${LABEL}1.${NC}  Recarregue o terminal para aplicar:"
echo -e "       ${ACCENT}exec \$SHELL${NC}\n"
echo -e "  ${LABEL}2.${NC}  O comando 'tunnel' não deve mais funcionar."
echo -e "$DIV\n"