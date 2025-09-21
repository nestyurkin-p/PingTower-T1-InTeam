FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app/notifier-service/dispatcher

COPY notifier-service/dispatcher/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY core /app/core
COPY database /app/database
COPY notifier-service /app/notifier-service

COPY .env /app/.env
CMD ["python", "main.py"]

