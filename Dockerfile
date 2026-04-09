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
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Cria o usuário 'tunnel' (uid 1000 coincide com o padrão do primeiro usuário no WSL)
RUN groupadd -g 1000 tunnel && \
    useradd -u 1000 -g tunnel -m -s /bin/bash tunnel

# Copia os arquivos primeiro para instalar as dependências
COPY --chown=tunnel:tunnel . .
RUN pip install --no-cache-dir .

# Copia e habilita o entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Mantemos como root para o entrypoint poder ajustar permissões de volumes montados
USER root

ENTRYPOINT ["/entrypoint.sh"]