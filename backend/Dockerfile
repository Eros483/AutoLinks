# ----- Backend Docker configuration @ backend/Dockerfile -----
FROM python:3.13-slim

WORKDIR /app/backend

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/ /app/backend/

RUN uv sync --frozen --no-dev

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD .venv/bin/celery -A backend.core.tasks worker --concurrency=4 --loglevel=info & \
    .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
