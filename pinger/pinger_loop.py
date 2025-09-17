import os, time, sys, json, socket, argparse, threading, uuid
from time import strftime
from pinger_checks import run_checks, CHECKS as DEFAULT_CHECKS

try:
    import pika # type: ignore
except Exception:
    pika = None

class RmqPublisher:
    def __init__(self,
                 url=None,
                 host=None, port=None, user=None, password=None, vhost="/",
                 exchange=None, exchange_type="direct",
                 routing_key=None,
                 queue=None,
                 publish_mode="errors",
                 persistent=True,
                 declare_passive=False,
                 heartbeat=30,
                 blocked_conn_timeout=30,
                 reconnect_delay=5):
        self.publish_mode = publish_mode
        self.persistent = persistent
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.routing_key = routing_key or (queue or "")
        self.queue = queue
        self.declare_passive = declare_passive
        self.reconnect_delay = reconnect_delay

        if url:
            self.params = pika.URLParameters(url)
        else:
            credentials = pika.PlainCredentials(user or "guest", password or "guest")
            self.params = pika.ConnectionParameters(
                host=host or "localhost",
                port=int(port or 5672),
                virtual_host=vhost or "/",
                credentials=credentials,
                heartbeat=heartbeat,
                blocked_connection_timeout=blocked_conn_timeout,
            )
        self.conn = None
        self.chan = None

    def _ensure_connection(self):
        if self.conn and self.conn.is_open and self.chan and self.chan.is_open:
            return
        while True:
            try:
                self.conn = pika.BlockingConnection(self.params)
                self.chan = self.conn.channel()
                if self.exchange:
                    self.chan.exchange_declare(exchange=self.exchange,
                                               exchange_type=self.exchange_type,
                                               durable=True,
                                               passive=self.declare_passive)
                if self.queue:
                    self.chan.queue_declare(queue=self.queue, durable=True, passive=self.declare_passive)
                    if self.exchange:
                        self.chan.queue_bind(queue=self.queue, exchange=self.exchange, routing_key=self.routing_key)
                return
            except Exception as e:
                print(f"[RMQ] connect error: {e}. Reconnecting in {self.reconnect_delay}s...", file=sys.stderr)
                time.sleep(self.reconnect_delay)

    def should_send(self, record):
        if self.publish_mode == "all":
            return True
        if self.publish_mode == "errors":
            return not record.get("ok", True)
        return False

    def publish(self, record: dict):
        if not pika:
            return 
        if not self.should_send(record):
            return
        self._ensure_connection()
        body = json.dumps(record, ensure_ascii=False).encode("utf-8")
        props = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2 if self.persistent else 1,
            message_id=str(uuid.uuid4()),
            headers={
                "service": record.get("env", {}).get("service", "site-monitor"),
                "url": record.get("url", ""),
                "ok": record.get("ok", False),
            },
        )
        try:
            self.chan.basic_publish(
                exchange=self.exchange or "",
                routing_key=self.routing_key or "",
                body=body,
                properties=props,
                mandatory=False
            )
        except Exception as e:
            print(f"[RMQ] publish error: {e}. Reconnecting...", file=sys.stderr)
            try:
                if self.conn: self.conn.close()
            except Exception:
                pass
            self.conn = self.chan = None
            self._ensure_connection()
            self.chan.basic_publish(
                exchange=self.exchange or "",
                routing_key=self.routing_key or "",
                body=body,
                properties=props,
                mandatory=False
            )

def main():
    parser = argparse.ArgumentParser(description="Циклический мониторинг URL с JSON-выводом и RabbitMQ")
    parser.add_argument("--url", nargs="?", default=os.getenv("URL"),
                        help="URL для мониторинга (или ENV URL)")
    parser.add_argument("--interval", type=int, default=int(os.getenv("INTERVAL", "60")),
                        help="интервал проверки в секундах")
    parser.add_argument("--format", choices=("json","text"), default=os.getenv("FORMAT","json"),
                        help="формат локального вывода (json|text)")
    parser.add_argument("--checks-json", default=os.getenv("CHECKS_JSON"),
                        help="JSON-строка для переопределения CHECKS")

    parser.add_argument("--rmq-url", default=os.getenv("RMQ_URL"))
    parser.add_argument("--rmq-host", default=os.getenv("RMQ_HOST"))
    parser.add_argument("--rmq-port", default=os.getenv("RMQ_PORT"))
    parser.add_argument("--rmq-user", default=os.getenv("RMQ_USER"))
    parser.add_argument("--rmq-pass", default=os.getenv("RMQ_PASS"))
    parser.add_argument("--rmq-vhost", default=os.getenv("RMQ_VHOST", "/"))
    parser.add_argument("--rmq-exchange", default=os.getenv("RMQ_EXCHANGE"))
    parser.add_argument("--rmq-exchange-type", default=os.getenv("RMQ_EXCHANGE_TYPE", "direct"))
    parser.add_argument("--rmq-routing-key", default=os.getenv("RMQ_ROUTING_KEY"))
    parser.add_argument("--rmq-queue", default=os.getenv("RMQ_QUEUE"))
    parser.add_argument("--rmq-publish-mode", choices=("errors","all"),
                        default=os.getenv("RMQ_PUBLISH_MODE","errors"))
    parser.add_argument("--rmq-passive", action="store_true", default=os.getenv("RMQ_PASSIVE","").lower()=="true",
                        help="не создавать, а только проверять существование сущностей")

    args = parser.parse_args()

    if not args.url:
        print("ERROR: URL is required (arg --url or ENV URL).")
        sys.exit(64)

    checks = DEFAULT_CHECKS.copy()
    if args.checks_json:
        try:
            overrides = json.loads(args.checks_json)
            checks.update(overrides)
        except Exception as e:
            print(f"WARNING: bad CHECKS_JSON: {e}", file=sys.stderr)

    host_identity = {
        "container_host": socket.gethostname(),
        "service": "site-monitor"
    }

    rmq = None
    if pika and (args.rmq_url or args.rmq_host or args.rmq_queue or args.rmq_exchange):
        rmq = RmqPublisher(
            url=args.rmq_url,
            host=args.rmq_host, port=args.rmq_port,
            user=args.rmq_user, password=args.rmq_pass, vhost=args.rmq_vhost,
            exchange=args.rmq_exchange, exchange_type=args.rmq_exchange_type,
            routing_key=args.rmq_routing_key, queue=args.rmq_queue,
            publish_mode=args.rmq_publish_mode,
            declare_passive=args.rmq_passive
        )

    try:
        while True:
            errors, metrics = run_checks(args.url, checks)
            ok = len(errors) == 0
            record = {
                "timestamp": strftime("%Y-%m-%dT%H:%M:%S"),
                "ok": ok,
                "url": args.url,
                "errors": errors,
                "metrics": metrics
            }

            if args.format == "json":
                print(json.dumps(record, ensure_ascii=False))
                
            else:
                if ok:
                    print(f"[{record['timestamp']}] [OK] {args.url} — passed")
                else:
                    print(f"[{record['timestamp']}] [FAIL] {args.url}")
                    for i, e in enumerate(errors, 1):
                        print(f"  {i}) {e['code']}: {e['message']} {e.get('details') or ''}")
            sys.stdout.flush()

            if rmq:
                rmq.publish(record)

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    main()
