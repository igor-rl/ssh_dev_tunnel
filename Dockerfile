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

# Criação do usuário 'tunnel'
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# Prepara os diretórios de configuração
RUN mkdir -p /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /home/tunnel/.dev_tunnel && \
    chmod 700 /home/tunnel/.dev_tunnel

# Copia o código para dentro da imagem
COPY --chown=tunnel:tunnel . .

# Instala o pacote (isso cria o executável 'tunnel' no PATH)
RUN pip install --no-cache-dir .

# Muda para o usuário não-root
USER tunnel

# O ENTRYPOINT chama o binário instalado pelo pip install .
ENTRYPOINT ["tunnel"]