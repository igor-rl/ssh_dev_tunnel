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

# Criação do usuário 'tunnel' (ID 1000 para bater com WSL/Linux)
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# Prepara os diretórios. 
# IMPORTANTE: O script de instalação usa /root/.dev_tunnel no volume, 
# mas como o usuário é 'tunnel', vamos ajustar para o HOME dele.
RUN mkdir -p /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /home/tunnel/.dev_tunnel && \
    chmod 700 /home/tunnel/.dev_tunnel

COPY --chown=tunnel:tunnel . .

RUN pip install --no-cache-dir .

# Muda para o usuário não-root
USER tunnel

# Usamos CMD em vez de ENTRYPOINT para dar flexibilidade ao seu script de instalação
CMD ["python3", "/app/main.py"]