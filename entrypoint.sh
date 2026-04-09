#!/bin/bash
set -e

# 1. Garante que o usuário tunnel (1000) possa ler o Docker Socket
if [ -e /var/run/docker.sock ]; then
    chown root:1000 /var/run/docker.sock || true
fi

# 2. Garante permissões na pasta do projeto
chown -R 1000:1000 /app

# 3. Verifica se um comando foi passado, caso contrário, segura o container vivo
if [ $# -eq 0 ]; then
    echo "--- Dev Tunnel pronto. Aguardando instruções... ---"
    exec gosu tunnel tail -f /dev/null
else
    exec gosu tunnel tunnel "$@"
fi