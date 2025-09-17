import pika
import json
import os
import time
from openai_wrapper import OpenAIWrapper

API_KEY = "sk-Z5H3GUqo6S4VeCy7p7YTWGCyRKVzqm16"
RABBIT_HOST = os.getenv("RABBIT_HOST", "localhost")

QUEUE_IN = "llm_requests"
QUEUE_OUT = "llm_responses"

llm = OpenAIWrapper(api_key=API_KEY)


def connect_with_retry(host, retries=10, delay=5):
    """Подключение к RabbitMQ с ретраями"""
    for i in range(1, retries + 1):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
            print("[✓] Подключение к RabbitMQ успешно")
            return connection
        except pika.exceptions.AMQPConnectionError as e:
            print(f"[!] Попытка {i}/{retries}: RabbitMQ недоступен, жду {delay}с...")
            time.sleep(delay)
    raise RuntimeError("Не удалось подключиться к RabbitMQ")


def on_message(channel, method, properties, body):
    try:
        data = json.loads(body)
        query = data.get("query", "")
        print(f"[x] Получено сообщение: {query}")

        result = llm.send_message(query)

        response = {"query": query, "response": result}
        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_OUT,
            body=json.dumps(response).encode("utf-8")
        )
        print(f"[✓] Отправлен результат: {result[:60]}...")

    except Exception as e:
        print("[!] Ошибка обработки сообщения:", e)


def main():
    connection = connect_with_retry(RABBIT_HOST, retries=12, delay=5)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_IN, durable=True)
    channel.queue_declare(queue=QUEUE_OUT, durable=True)
    channel.basic_consume(queue=QUEUE_IN, on_message_callback=on_message, auto_ack=True)

    print("[*] Ожидание сообщений...")
    channel.start_consuming()


if __name__ == "__main__":
    main()
