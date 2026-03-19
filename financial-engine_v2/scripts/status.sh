#!/usr/bin/env bash

echo "[STATUS] Backend:"
pgrep -af "uvicorn .*app.main:app" || echo "Not running"

echo "[STATUS] Worker:"
pgrep -af "celery .*app.celery_app.celery" || echo "Not running"
