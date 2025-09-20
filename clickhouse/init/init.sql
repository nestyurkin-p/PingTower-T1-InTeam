-- Создаём базу, если ещё нет
DROP DATABASE IF EXISTS monitor;
CREATE DATABASE monitor;

-- Таблица для временных рядов логов пингера
CREATE TABLE site_logs
(
    id UInt64,
    url String,
    name String,
    traffic_light LowCardinality(String),
    timestamp DateTime,
    http_status Nullable(Int32),
    latency_ms Nullable(Int32),
    ping_ms Nullable(Float32),         -- 👈 теперь Nullable
    ssl_days_left Nullable(Int32),
    dns_resolved UInt8,
    redirects Nullable(Int32),
    errors_last Nullable(Int32),
    ping_interval UInt32
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(timestamp)
ORDER BY (id, timestamp);
