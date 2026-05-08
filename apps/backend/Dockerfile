FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
  && rm -rf /var/lib/apt/lists/*

COPY apps/backend/requirements.txt /app/apps/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/backend/requirements.txt

COPY apps /app/apps
COPY packages /app/packages
COPY db/professor_match_publications.sqlite /app/seed-db/professor_match_publications.sqlite

EXPOSE 8000
CMD ["sh", "-c", "mkdir -p /app/db && if [ ! -f /app/db/professor_match_publications.sqlite ]; then cp /app/seed-db/professor_match_publications.sqlite /app/db/professor_match_publications.sqlite; fi && uvicorn apps.backend.app.main:app --host 0.0.0.0 --port 8000"]
