import pika
import json

RABBIT_HOST = "localhost"
QUEUE_IN = "llm_requests"

def send_query(query: str):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_IN, durable=True)

    message = {"query": query}
    channel.publish(
        exchange="",
        routing_key=QUEUE_IN,
        body=json.dumps(message).encode("utf-8"),
    )
    print(f"[>] Отправлено: {query}")
    connection.close()

if __name__ == "__main__":
    send_query("Придумай шутку про Python")
