#!/bin/bash

# Cores para o terminal
BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
RED='\033[38;5;196m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalando/Atualizando SSH DEV TUNNEL...${NC}"

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Erro: Python3 não encontrado. Por favor, instale o Python antes.${NC}"
    exit 1
fi

# Instala/Atualiza direto do seu repositório
pip install --upgrade git+https://github.com/igor-rl/ssh_dev_tunnel.git

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Instalação concluída com sucesso!${NC}"
    echo -e "Digite ${BLUE}'tunnel'${NC} para começar.\n"
else
    echo -e "\n${RED}❌ Ocorreu um erro durante a instalação.${NC}"
    exit 1
fi