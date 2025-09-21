вот обновлённый `README.md` для твоего микросервиса — сразу в твоём стиле и с учётом всех наших правок, Windows/PowerShell и тестов.

---

# notifier-service


## Структура

```
notifier-service/
└─ tg-bot/                      # Telegram-нотифаер
   ├─ bot.py                    # Точка входа
   ├─ services/                 # Подключение к брокеру, consumer (aio-pika)
   ├─ handlers/
   ├─ utils/                    # Форматирование алертов, работа с подписками
   ├─ lexicon/                  # Шаблоны сообщений
   ├─ tests/                    # Локальные тесты публикации (aio-pika / FastStream)
   ├─ requirements.txt
   ├─ Dockerfile                # Образ для tg-нотифаера
   └─ .env.example
```

### Быстрый стенд брокеров (Docker Desktop)

```powershell
# RabbitMQ + web-UI
docker run -d --name rabbit `
  -p 5672:5672 -p 15672:15672 `
  -e RABBITMQ_DEFAULT_USER=root `
  -e RABBITMQ_DEFAULT_PASS=toor `
  rabbitmq:3.13-management

```

UI: [http://localhost:15672](http://localhost:15672) (логин/пароль: `root` / `toor`)

## Запуск локально

### Windows PowerShell

```powershell
cd .\notifier-service\tg-bot

# venv (можно использовать общий .venv в корне проекта — не принципиально)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# deps (uvloop на Windows не ставится — в requirements уже помечен как non-win)
python -m pip install --upgrade pip
python -m pip install -r .\requirements.txt

Copy-Item .\.env.example .\.env
# впиши TG_TOKEN и прочее

python .\bot.py
```

### Linux/macOS (bash)

```bash
cd notifier-service/tg-bot
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

После старта напиши боту в Telegram `/start`, затем `/ping` → должно ответить `pong`.

## Docker

```bash
cd notifier-service/tg-bot
docker build -t notifier-tg:latest .
docker run --rm \
  --env-file .env \
  --network host \            # для локалки на Linux
  notifier-tg:latest
```


## Формат входящих сообщений

Ожидается JSON (типизация мягкая, форматтер берёт лучшие догадки):

* `severity` / `level`
* `status` / `event_type`
* `monitor_name` / `monitor_id` / `service`
* `target` / `url` / `host`
* `reason` / `message`
* `incident_id` / `event_id`

Любой другой JSON тоже отобразится — всё, что найдено, будет красиво оформлено (HTML).

## Подписки


* `/start` — подписывает текущий чат
* `/stop` — отписывает
* `/ping` — проверка

## Тестирование публикаций

Тесты лежат в `tg-bot/tests/`.

### 1) Публикация в **exchange** (рекомендуется для реального роутинга)

```bash
cd notifier-service/tg-bot/tests
python publish_test.py
```

Публикует в `exchange = pinger.events` с `routing_key = alert.triggered`. Очередь привязана `rk = #`, поэтому событие попадёт.

### 2) Публикация **напрямую в очередь** (шорткат)

```bash
# однажды установи faststream:
pip install "faststream[rabbit]"

cd notifier-service/tg-bot/tests
python alert_message_test.py
```

Публикует в default exchange с `routing_key = имя очереди` (жёсткая привязка к имени `RABBIT_QUEUE`).
