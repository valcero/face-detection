#!/bin/sh
set -eu

echo "Running migrations..."
until alembic upgrade head; do
  echo "Migrations failed (db not ready?). Retrying in 2s..."
  sleep 2
done

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

