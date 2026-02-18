FROM python:3.11-slim
WORKDIR /app_worker
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app_worker/requirements.txt
RUN pip install --no-cache-dir -r /app_worker/requirements.txt
COPY . /app_worker
CMD ['celery','-A','app.celery_app.celery','worker','--loglevel=INFO','-Q','default']
