# syntax=docker/dockerfile:1
# Backend image — shared by the API, the Celery worker, and the migration
# one-shot. The process each runs is chosen via `command` in compose.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first so the layer caches across code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code (alembic.ini + app/ + scripts/). .dockerignore keeps venvs/caches out.
COPY . .

# Run as a non-root user.
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8080

# Default = API. The worker and migrate services override `command`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
