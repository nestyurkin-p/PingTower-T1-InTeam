FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

# cron-задачa
RUN echo "0 4 * * * root python /app/archive.py >> /var/log/cron.log 2>&1" > /etc/cron.d/archiver \
 && chmod 0644 /etc/cron.d/archiver \
 && crontab /etc/cron.d/archiver


CMD ["cron", "-f"]