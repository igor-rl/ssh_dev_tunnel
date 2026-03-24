#!/bin/bash

BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
YELLOW='\033[38;5;220m'
NC='\033[0m'

echo -e "${BLUE}🗑️  Desinstalando SSH DEV TUNNEL (Precifica)...${NC}"

# 1. Detectar Perfil do Shell
if [ -n "$ZSH_VERSION" ]; then PROFILE="$HOME/.zshrc"
else PROFILE="$HOME/.bash_profile"; fi

# 2. Remover o Alias do arquivo de perfil
if [ -f "$PROFILE" ]; then
    # Remove a linha que contém o alias do tunnel
    sed -i.bak '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    echo -e "${GREEN}✅ Atalho 'tunnel' removido de $PROFILE${NC}"
fi

# 3. Perguntar sobre os dados (Servidores cadastrados e PEMs)
echo -e "${YELLOW}❓ Deseja apagar também as configurações e servidores salvos? (y/N)${NC}"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    rm -rf ~/.dev_tunnel_config
    rm -rf ~/.dev_tunnel
    echo -e "${GREEN}✅ Pasta de configurações removida.${NC}"
else
    echo -e "${BLUE}ℹ️  Configurações mantidas em ~/.dev_tunnel_config${NC}"
fi

echo -e "\n${GREEN}✨ Desinstalação concluída! Reinicie o terminal para aplicar.${NC}"