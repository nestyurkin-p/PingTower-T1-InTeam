FROM python:3.11-slim

# Создаем директорию
WORKDIR /app

# Копируем файлы
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Запуск ноды
CMD ["python", "worker.py"]
