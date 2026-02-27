FROM python:3.11-slim
WORKDIR /app_worker
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app_worker/requirements.txt
RUN pip install --no-cache-dir -r /app_worker/requirements.txt
RUN groupadd -g 1000 appuser && useradd -m -u 1000 -g 1000 -s /bin/bash appuser
COPY . /app_worker
ENV PYTHONPATH=/app_backend:/app_worker
USER appuser
CMD ["celery", "-A", "worker_app.celery_app:celery", "worker", "--loglevel=INFO", "-Q", "default"]
