# ─── Estágio de Produção ───────────────────────────────────────
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.authors="Igor Lage"
LABEL org.opencontainers.image.description="SSH Dev Tunnel CLI - Precifica"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# 1. Criação do usuário 'tunnel' para evitar o uso de ROOT
# Usamos o ID 1000 que é o padrão do primeiro usuário no WSL/Linux
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# 2. Prepara os diretórios com as permissões corretas
RUN mkdir -p /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /home/tunnel/.dev_tunnel && \
    chmod 700 /home/tunnel/.dev_tunnel

COPY --chown=tunnel:tunnel . .

RUN pip install --no-cache-dir .

# Muda para o usuário não-root
USER tunnel

# O script agora usará /home/tunnel/.dev_tunnel como BASE_DIR
ENTRYPOINT ["tunnel"]