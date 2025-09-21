FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

RUN pip install --no-cache-dir poetry

WORKDIR /app/broker

COPY broker/pyproject.toml /app/broker/pyproject.toml
COPY broker/poetry.lock /app/broker/poetry.lock
RUN poetry config --no-cache virtualenvs.create false \
    && poetry install --no-cache --no-root --no-interaction --no-ansi --only main

COPY core /app/core
COPY broker /app/broker

COPY .env /app/.env
CMD ["poetry", "run", "python", "broker.py"]

