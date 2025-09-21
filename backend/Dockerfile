FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app/backend

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY core /app/core
COPY database /app/database
COPY backend /app/backend

COPY .env /app/.env
CMD ["python", "-m", "app.main"]

