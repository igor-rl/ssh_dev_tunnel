# ─── Estágio de Produção ───────────────────────────────────────
FROM python:3.12-slim AS production
LABEL org.opencontainers.image.authors="Igor Lage"
LABEL org.opencontainers.image.description="SSH Dev Tunnel CLI - Precifica"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema
# gosu: troca de usuário segura no entrypoint (sem sudo, sem setuid)
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Cria o usuário 'tunnel' (uid/gid 1000 — padrão WSL/Linux)
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# Copia e instala o pacote Python
COPY --chown=tunnel:tunnel . .
RUN pip install --no-cache-dir .

# Copia e habilita o entrypoint (roda como root para corrigir permissões do volume)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# O entrypoint roda como root, ajusta /home/tunnel/.dev_tunnel e faz exec como tunnel.
# Isso resolve o PermissionError em volumes Docker nomeados (criados com dono root).
USER root

ENTRYPOINT ["/entrypoint.sh"]