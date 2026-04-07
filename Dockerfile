# ─── Estágio de Desenvolvimento ──────────────────────────────────
FROM python:3.12-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    git \
    && rm -rf /var/lib/apt/lists/*

# ─── Usuário não-root ─────────────────────────────────────────────
RUN groupadd --gid 1000 tunnel && \
    useradd --uid 1000 --gid tunnel --shell /bin/bash --create-home tunnel

COPY setup.py .
COPY src/ ./src/

# Instala dependências (inclui keyring) e o pacote em modo editável
RUN pip install --no-cache-dir -e .

# Diretório de dados pertencente ao usuário tunnel
RUN mkdir -p /home/tunnel/.dev_tunnel && \
    chmod 700 /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /app

USER tunnel

CMD ["tail", "-f", "/dev/null"]


# ─── Estágio de Produção ───────────────────────────────────────
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.authors="Igor Lage"
LABEL org.opencontainers.image.description="SSH Dev Tunnel CLI - Precifica"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    && rm -rf /var/lib/apt/lists/*

# ─── Usuário não-root ─────────────────────────────────────────────
RUN groupadd --gid 1000 tunnel && \
    useradd --uid 1000 --gid tunnel --shell /bin/bash --create-home tunnel

COPY . .

RUN pip install --no-cache-dir .

# Diretório de dados pertencente ao usuário tunnel
RUN mkdir -p /home/tunnel/.dev_tunnel && \
    chmod 700 /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /home/tunnel/.dev_tunnel && \
    chown -R tunnel:tunnel /app

USER tunnel

ENTRYPOINT ["tunnel"]