FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl libgtk-3-0t64 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
RUN python -m playwright install --with-deps chromium && camoufox fetch --browserforge
COPY backend/ /app
COPY shared/ /app/shared
COPY cockpit/ /app/cockpit
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
