# ----- Backend Docker configuration @ backend/Dockerfile -----
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY backend/pyproject.toml backend/uv.lock /app/backend/

RUN cd /app/backend && uv sync --frozen --no-dev

COPY backend/ /app/backend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD cd /app/backend && \
    uv run celery -A backend.core.tasks worker --concurrency=4 --loglevel=info & \
    uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
