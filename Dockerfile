# ─── Estágio de Produção ───────────────────────────────────────
FROM python:3.12-slim AS production
LABEL org.opencontainers.image.authors="Igor Lage"
LABEL org.opencontainers.image.description="SSH Dev Tunnel CLI - Precifica"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# Cria o usuário 'tunnel' (uid/gid 1000 — padrão WSL/Linux)
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# Copia e instala o pacote Python
COPY --chown=tunnel:tunnel . .
RUN pip install --no-cache-dir .

# NÃO criamos /home/tunnel/.dev_tunnel aqui.
# Esse diretório será montado via volume pelo host (-v ~/.dev_tunnel_config:/home/tunnel/.dev_tunnel).
# Se o Docker criasse o diretório com root antes da montagem, o uid 1000
# não teria permissão de escrita — causando PermissionError no Python.
# O host garante mkdir + chmod 700 antes de subir o container (ver install.sh).

USER tunnel

ENTRYPOINT ["tunnel"]