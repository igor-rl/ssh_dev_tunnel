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

COPY setup.py .
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

RUN mkdir -p /root/.dev_tunnel && chmod 700 /root/.dev_tunnel

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

COPY . .

RUN pip install --no-cache-dir .

RUN mkdir -p /root/.dev_tunnel && chmod 700 /root/.dev_tunnel

ENTRYPOINT ["tunnel"]