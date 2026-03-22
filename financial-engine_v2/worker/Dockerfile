# syntax=docker/dockerfile:1
FROM python:3.11-slim
WORKDIR /app_worker
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app_worker/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app_worker/requirements.txt
COPY . /app_worker
CMD ["celery", "-A", "app.celery_app.celery", "worker", "--loglevel=INFO", "-Q", "ingest,embed,score,llm_cpu,llm_gpu"]
