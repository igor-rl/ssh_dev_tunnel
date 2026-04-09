#!/bin/bash
# Roda como root, corrige permissões do volume e faz exec como usuário tunnel.
# Necessário porque volumes Docker nomeados são criados com dono root.
set -e

TARGET_DIR="/home/tunnel/.dev_tunnel"

# Garante que o diretório existe e pertence ao uid/gid 1000 (tunnel)
mkdir -p "$TARGET_DIR"
chown -R 1000:1000 "$TARGET_DIR"
chmod 700 "$TARGET_DIR"

# Substitui o processo atual pelo comando tunnel, rodando como usuário tunnel
exec gosu tunnel tunnel "$@"