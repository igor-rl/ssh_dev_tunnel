FROM python:3.12-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de configuração primeiro para aproveitar o cache do Docker
COPY setup.py .
COPY src/ ./src/

# Instala o pacote globalmente
RUN pip install --no-cache-dir -e .

# Cria a pasta de config
RUN mkdir -p /root/.dev_tunnel && chmod 700 /root/.dev_tunnel

CMD ["tail", "-f", "/dev/null"]