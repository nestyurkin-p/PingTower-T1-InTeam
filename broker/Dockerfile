FROM python:3.13-slim

RUN pip install --no-cache-dir "poetry"

COPY pyproject.toml poetry.lock ./
RUN poetry config --no-cache virtualenvs.create false && poetry install --no-cache --no-root --no-interaction --no-ansi --only main

COPY . .

CMD ["poetry", "run", "python",  "broker.py"]