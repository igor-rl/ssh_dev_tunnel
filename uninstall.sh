#!/bin/bash

BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
YELLOW='\033[38;5;220m'
NC='\033[0m'

echo -e "${BLUE}🗑️  Desinstalando SSH DEV TUNNEL (Precifica)...${NC}"

# 1. Detectar Perfil
[ -n "$ZSH_VERSION" ] && PROFILE="$HOME/.zshrc" || PROFILE="$HOME/.bash_profile"

# 2. Remover o Alias (Usa comando compatível com Mac e Linux)
if [ -f "$PROFILE" ]; then
    sed -i.bak '/alias tunnel=/d' "$PROFILE" 2>/dev/null
    echo -e "${GREEN}✅ Atalho 'tunnel' removido de $PROFILE${NC}"
fi

# 3. Limpar pastas de dados
echo -e "${YELLOW}❓ Deseja apagar também as configurações e servidores salvos? (y/N)${NC}"
# O </dev/tty força o read a olhar para o teclado, não para o curl
read -r response </dev/tty

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    rm -rf ~/.dev_tunnel_config
    rm -rf ~/.dev_tunnel
    echo -e "${GREEN}✅ Pasta de configurações removida.${NC}"
else
    echo -e "${BLUE}ℹ️  Configurações mantidas.${NC}"
fi

echo -e "\n${GREEN}✨ Desinstalação concluída!${NC}"