#!/bin/bash

# Cores para o terminal
BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
RED='\033[38;5;196m'
YELLOW='\033[38;5;220m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Instalando/Atualizando SSH DEV TUNNEL (Precifica)...${NC}"

# 1. Verifica se o Python3 está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Erro: Python3 não encontrado. Instale com 'brew install python' no Mac.${NC}"
    exit 1
fi

# 2. Identifica o gerenciador de pacotes correto (pip3 ou pip)
PIP_CMD=$(command -v pip3 || command -v pip)

if [ -z "$PIP_CMD" ]; then
    echo -e "${YELLOW}⚠️ Pip não encontrado. Tentando ativar via ensurepip...${NC}"
    python3 -m ensurepip --upgrade --user
    PIP_CMD=$(command -v pip3 || command -v pip)
fi

# 3. Instala/Atualiza direto do seu repositório
# Usamos --user para evitar problemas de permissão no macOS/Linux
$PIP_CMD install --upgrade --user git+https://github.com/igor-rl/ssh_dev_tunnel.git

if [ $? -eq 0 ]; then
    # 4. Garante que a pasta de scripts do Python está no PATH do usuário
    PYTHON_BIN_PATH=$(python3 -m site --user-base)/bin
    
    if [[ ":$PATH:" != *":$PYTHON_BIN_PATH:"* ]]; then
        echo -e "${YELLOW}🔧 Adicionando comando 'tunnel' ao seu perfil do terminal...${NC}"
        echo "export PATH=\"\$PATH:$PYTHON_BIN_PATH\"" >> ~/.zshrc
        echo "export PATH=\"\$PATH:$PYTHON_BIN_PATH\"" >> ~/.bash_profile
        export PATH="$PATH:$PYTHON_BIN_PATH"
    fi

    echo -e "\n${GREEN}✅ Instalação concluída com sucesso!${NC}"
    echo -e "💡 Se o comando não funcionar agora, rode: ${BLUE}source ~/.zshrc${NC}"
    echo -e "🚀 Digite ${BLUE}'tunnel'${NC} para começar.\n"
else
    echo -e "\n${RED}❌ Ocorreu um erro durante a instalação.${NC}"
    exit 1
fi