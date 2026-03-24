#!/bin/bash

# ─── Configurações ─────────────────────────────────────────────
# IMPORTANTE: Substitua 'seu-usuario' pelo seu nome no GitHub
IMAGE="ghcr.io/seu-usuario/ssh_dev_tunnel:latest"
CONTAINER_NAME="dev-tunnel"
LOCAL_CONFIG_DIR="$HOME/.dev_tunnel_config"
PORT=2222

# Cores para o terminal
BLUE='\033[38;5;75m'
GREEN='\033[38;5;114m'
YELLOW='\033[38;5;220m'
NC='\033[0m'

echo -e "${BLUE}🚀 Iniciando SSH Dev Tunnel (Precifica)...${NC}"

# 1. Detectar o Caminho do Host (Mac vs Windows)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    CURRENT_PATH=$(cygpath -m "$(pwd)")
    echo -e "${YELLOW}💻 Ambiente Windows detectado (Git Bash)${NC}"
else
    CURRENT_PATH=$(pwd)
    echo -e "${YELLOW}🍎 Ambiente macOS/Linux detectado${NC}"
fi

# 2. Garante que a pasta de configuração local existe (Persistência)
if [ ! -d "$LOCAL_CONFIG_DIR" ]; then
    mkdir -p "$LOCAL_CONFIG_DIR"
fi

# 3. Roda o Docker
# -v Mapeia a config para o Home do usuário
# -v Mapeia a pasta atual para o container salvar o .code-workspace
# -e Passa o caminho real para o Python traduzir o link do Cursor
docker run -it --rm \
  --name $CONTAINER_NAME \
  -p $PORT:$PORT \
  -v "$LOCAL_CONFIG_DIR:/root/.dev_tunnel" \
  -v "$CURRENT_PATH:/app" \
  -e HOST_PROJECT_PATH="$CURRENT_PATH" \
  $IMAGE

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Sessão encerrada com sucesso.${NC}"
fi