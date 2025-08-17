
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ARG APP_USER=appuser
ARG APP_HOME=/app
RUN useradd -m -s /bin/bash ${APP_USER}
WORKDIR ${APP_HOME}

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

ENV GUNICORN_WORKERS=3 \
    GUNICORN_TIMEOUT=120 \
    MAX_CONCURRENCY=4

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

USER ${APP_USER}


CMD ["bash", "-lc", "gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS} \
    --timeout ${GUNICORN_TIMEOUT}"]
