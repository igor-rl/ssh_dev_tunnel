#!/bin/bash

# Cores e Símbolos
BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
YELLOW='\033[38;5;220m'
RED='\033[38;5;196m'
NC='\033[0m'
BOLD='\033[1m'

# Configurações do GitHub
REPO_URL="https://github.com/igor-rl/ssh_dev_tunnel.git"
IMAGE="ghcr.io/igor-rl/ssh_dev_tunnel:latest"

# Limpa qualquer input residual no buffer antes de começar
while read -r -t 0; do read -r; done

# 1. Identificar Perfil do Shell
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bash_profile"; fi
touch "$PROFILE"

# 2. Detectar Dependências
HAS_DOCKER=false
HAS_PYTHON=false
if command -v docker &> /dev/null; then HAS_DOCKER=true; fi
if command -v python3 &> /dev/null; then HAS_PYTHON=true; fi

# 3. Montar Opções do Menu
options=()
if [ "$HAS_DOCKER" = true ]; then options+=("Docker (Recomendado - Isolado e Rápido)"); fi
if [ "$HAS_PYTHON" = true ]; then options+=("Python Local (Requer sshpass instalado)"); fi
options+=("Sair")

# Função de Menu Interativo (Setinhas)
selected=0
draw_menu() {
    clear
    echo -e "${BLUE}${BOLD}🚀 INSTALADOR SSH DEV TUNNEL (Precifica)${NC}"
    echo -e "${BLUE}──────────────────────────────────────────────────${NC}"
    echo -e "Como você deseja instalar a ferramenta?\n"
    
    for i in "${!options[@]}"; do
        if [ "$i" -eq "$selected" ]; then
            echo -e "  ${BLUE}▶ ${BOLD}${options[$i]}${NC}"
        else
            echo -e "    ${options[$i]}"
        fi
    done
    echo -e "\n${NC}Use as setas [↑↓] e aperte [ENTER] para confirmar."
}

# Loop do Menu
while true; do
    draw_menu
    # O </dev/tty força o bash a ler o teclado do usuário mesmo via curl
    read -rsn3 key </dev/tty
    case "$key" in
        $'\x1b\x5b\x41') ((selected--)); [ $selected -lt 0 ] && selected=$((${#options[@]} - 1)) ;; # Up
        $'\x1b\x5b\x42') ((selected++)); [ $selected -ge ${#options[@]} ] && selected=0 ;;         # Down
        "") break ;; # Enter
        $'\x0a') break ;; # Enter alternativo
    esac
done

CHOICE="${options[$selected]}"

# 4. Execução da Escolha
if [[ "$CHOICE" == *"Docker"* ]]; then
    echo -e "\n${BLUE}🐳 Configurando atalho via Docker...${NC}"
    
    # Remove alias antigo de forma compatível (Mac/Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    else
        sed -i '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    fi
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        # Windows
        CMD="alias tunnel='winpty docker run -it --rm --pull always -p 2222:2222 -v ~/.dev_tunnel_config:/root/.dev_tunnel -v \"\$(cygpath -m \"\$(pwd)\"):/app\" -e HOST_PROJECT_PATH=\"\$(cygpath -m \"\$(pwd)\")\" $IMAGE'"
    else
        # Mac/Linux
        CMD="alias tunnel='docker run -it --rm --pull always -p 2222:2222 -v ~/.dev_tunnel_config:/root/.dev_tunnel -v \"\$(pwd):/app\" -e HOST_PROJECT_PATH=\"\$(pwd)\" $IMAGE'"
    fi
    echo "$CMD" >> "$PROFILE"
    echo -e "${GREEN}✅ Atalho Docker configurado!${NC}"

elif [[ "$CHOICE" == *"Python"* ]]; then
    echo -e "\n${BLUE}🐍 Instalando via Python Local...${NC}"
    PIP_CMD=$(command -v pip3 || command -v pip)
    $PIP_CMD install --upgrade --user "git+$REPO_URL"
    
    BIN_PATH=$(python3 -m site --user-base)/bin
    if [[ ":$PATH:" != *":$BIN_PATH:"* ]]; then
        echo "export PATH=\"\$PATH:$BIN_PATH\"" >> "$PROFILE"
    fi
    echo -e "${GREEN}✅ Instalação Local concluída!${NC}"

else
    echo -e "\nInstalação cancelada."
    exit 0
fi

echo -e "\n${YELLOW}💡 Quase lá! Reinicie seu terminal ou rode:${NC} source $PROFILE"
echo -e "🚀 Depois, digite ${BLUE}'tunnel'${NC} para começar.\n"