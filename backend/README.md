# backend-service

FastAPI + FastStream микросервис: подписывается на события из `pinger.events` и `llm.events`,
складывает их в PostgreSQL (асинхронно) и отдаёт последние N логов через REST.

## Быстрый старт (dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# брокеры для локалки:
# docker run -d --name rabbit -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=root -e RABBITMQ_DEFAULT_PASS=toor rabbitmq:3.13-management
# docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=notifier postgres:16
python -m app.main
```
REST: `GET /logs?limit=50`
