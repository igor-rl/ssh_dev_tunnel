#!/bin/bash
set -e

# ─────────────────────────────────────────────────────────────────
# release.sh — bump de versão + commit + tag + push, num comando só.
#
# Uso:
#   ./release.sh "fix: issue: descrição da mudança"
#   ./release.sh "feat: nova tela de X" --minor
#   ./release.sh "breaking: Y"          --major
#
# Sem flag, bump é de PATCH (X.Y.Z -> X.Y.Z+1).
# ─────────────────────────────────────────────────────────────────

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

DIV="${DIVIDER}─────────────────────────────────────────────────────────────────${NC}"

ok()   { echo -e "  ${SUCCESS}✔  $1${NC}"; }
err()  { echo -e "  ${ERROR}✘  $1${NC}"; }
warn() { echo -e "  ${WARN}⚠  $1${NC}"; }
info() { echo -e "  ${DIM}$1${NC}"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

CONFIG_FILE="src/config.py"
SETUP_FILE="setup.py"

# ─── Args ──────────────────────────────────────────────────────
# Uso:
#   ./release.sh "msg"                 → bump de patch (padrão)
#   ./release.sh "msg" --minor|--major → bump de minor/major
#   ./release.sh "msg" 3.9.0           → define a versão exata
MSG="$1"
BUMP="patch"
EXPLICIT_VERSION=""

if [ -z "$MSG" ]; then
  err "Faltou a mensagem do commit."
  info "Uso: ./release.sh \"fix: issue: descrição\" [--minor|--major|X.Y.Z]"
  exit 1
fi

case "$2" in
  --minor) BUMP="minor" ;;
  --major) BUMP="major" ;;
  "" | --patch) BUMP="patch" ;;
  [0-9]*.[0-9]*.[0-9]*)
    if [[ "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      EXPLICIT_VERSION="$2"
    else
      err "Versão inválida: $2 (use o formato X.Y.Z)"; exit 1
    fi
    ;;
  *) err "Argumento desconhecido: $2 (use --minor, --major ou uma versão X.Y.Z)"; exit 1 ;;
esac

# ─── Branch e working tree ────────────────────────────────────
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
  warn "Você não está na branch 'main' (está em '$CURRENT_BRANCH')."
  echo -e "  ${BOLD}${WARN}Continuar mesmo assim? (s/N)${NC}  \c"
  read -r resp </dev/tty
  [[ "$resp" =~ ^([sS])$ ]] || { echo -e "\n  ${DIM}Cancelado.${NC}\n"; exit 0; }
fi

# ─── Detecta e valida versão atual ────────────────────────────
CUR_CONFIG=$(grep -oE '__version__ = "[0-9]+\.[0-9]+\.[0-9]+"' "$CONFIG_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
CUR_SETUP=$(grep -oE 'version="[0-9]+\.[0-9]+\.[0-9]+"' "$SETUP_FILE" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')

if [ -z "$CUR_CONFIG" ] || [ -z "$CUR_SETUP" ]; then
  err "Não consegui detectar a versão atual em $CONFIG_FILE ou $SETUP_FILE."
  exit 1
fi

if [ "$CUR_CONFIG" != "$CUR_SETUP" ]; then
  err "Versões desincronizadas: $CONFIG_FILE=$CUR_CONFIG  vs  $SETUP_FILE=$CUR_SETUP"
  info "Corrija manualmente antes de rodar o release."
  exit 1
fi

CURRENT="$CUR_CONFIG"

if [ -n "$EXPLICIT_VERSION" ]; then
  NEW="$EXPLICIT_VERSION"
  BUMP_LABEL="manual"

  # Sanity check: avisa (mas não bloqueia) se a versão informada não for maior que a atual.
  IFS='.' read -r CUR_MAJOR CUR_MINOR CUR_PATCH <<< "$CURRENT"
  IFS='.' read -r NEW_MAJOR NEW_MINOR NEW_PATCH <<< "$NEW"
  CUR_NUM=$((CUR_MAJOR * 1000000 + CUR_MINOR * 1000 + CUR_PATCH))
  NEW_NUM=$((NEW_MAJOR * 1000000 + NEW_MINOR * 1000 + NEW_PATCH))
  if [ "$NEW_NUM" -le "$CUR_NUM" ]; then
    warn "Versão informada (v$NEW) não é maior que a atual (v$CURRENT)."
    echo -e "  ${BOLD}${WARN}Continuar mesmo assim? (s/N)${NC}  \c"
    read -r resp </dev/tty
    [[ "$resp" =~ ^([sS])$ ]] || { echo -e "\n  ${DIM}Cancelado.${NC}\n"; exit 0; }
  fi
else
  IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"
  case "$BUMP" in
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    patch) PATCH=$((PATCH + 1)) ;;
  esac
  NEW="$MAJOR.$MINOR.$PATCH"
  BUMP_LABEL="$BUMP"
fi

TAG="v$NEW"
COMMIT_MSG="$TAG: $MSG"

echo -e "$DIV"
echo -e "  ${BOLD}${INFO}RELEASE${NC}"
echo -e "$DIV"
echo -e "  ${LABEL}Versão atual:${NC}   v$CURRENT"
echo -e "  ${LABEL}Nova versão:${NC}    ${ACCENT}${BOLD}$TAG${NC}  ${DIM}($BUMP_LABEL)${NC}"
echo -e "  ${LABEL}Commit:${NC}         $COMMIT_MSG"
echo -e "$DIV"

# ─── Atualiza os arquivos de versão ───────────────────────────
if [[ "$OSTYPE" == "darwin"* ]]; then
  sed -i '' "s/__version__ = \"$CURRENT\"/__version__ = \"$NEW\"/" "$CONFIG_FILE"
  sed -i '' "s/version=\"$CURRENT\"/version=\"$NEW\"/" "$SETUP_FILE"
else
  sed -i "s/__version__ = \"$CURRENT\"/__version__ = \"$NEW\"/" "$CONFIG_FILE"
  sed -i "s/version=\"$CURRENT\"/version=\"$NEW\"/" "$SETUP_FILE"
fi
ok "Versão atualizada em $CONFIG_FILE e $SETUP_FILE."

# ─── Mostra o que vai ser commitado ────────────────────────────
echo ""
git status --short
echo ""
echo -e "  ${BOLD}${WARN}Confirmar commit + tag + push? (s/N)${NC}  \c"
read -r confirm </dev/tty
if [[ ! "$confirm" =~ ^([sS])$ ]]; then
  warn "Cancelado. Revertendo bump de versão..."
  git checkout -- "$CONFIG_FILE" "$SETUP_FILE"
  exit 0
fi

# ─── Commit, tag e push ────────────────────────────────────────
git add .
git commit -m "$COMMIT_MSG"
git tag "$TAG"

echo ""
echo -e "  ${BOLD}${WARN}Push para origin/main com a tag? (s/N)${NC}  \c"
read -r push_confirm </dev/tty
if [[ ! "$push_confirm" =~ ^([sS])$ ]]; then
  warn "Commit e tag criados localmente, mas NÃO enviados."
  info "Para enviar depois: git push origin main --tags"
  exit 0
fi

git push origin main --tags
echo ""
ok "Release $TAG publicada."
