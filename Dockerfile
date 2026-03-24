FROM python:3.12-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/local/bin/python3 /usr/local/bin/py

COPY . .

RUN pip install -e .

RUN mkdir -p /root/.dev_tunnel && chmod 700 /root/.dev_tunnel

CMD ["tail", "-f", "/dev/null"]