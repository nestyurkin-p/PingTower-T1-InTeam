import pika
import json

RABBIT_HOST = "localhost"
QUEUE_OUT = "llm_responses"

def callback(ch, method, properties, body):
    response = json.loads(body)
    print(f"[<] Получен ответ: {response['response']}")

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_OUT, durable=True)

    channel.basic_consume(queue=QUEUE_OUT, on_message_callback=callback, auto_ack=True)

    print("[*] Ожидание ответов...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
