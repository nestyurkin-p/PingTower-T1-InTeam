-- init.sql для Postgres (./postgres/init/init.sql)

CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,             -- 👈 теперь уникальный
    name TEXT NOT NULL,
    com JSONB DEFAULT '{}'::jsonb,        -- любые дополнительные настройки
    last_traffic_light TEXT,              -- последний статус (green/orange/red)
    history JSONB DEFAULT '[]'::jsonb,    -- история последних проверок
    ping_interval INTEGER DEFAULT 30,     -- частота проверки (в секундах)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для ускорения выборок
CREATE INDEX IF NOT EXISTS idx_sites_url ON sites(url);
CREATE INDEX IF NOT EXISTS idx_sites_name ON sites(name);

-- Триггер для автообновления updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sites_updated_at ON sites;
CREATE TRIGGER trg_sites_updated_at
BEFORE UPDATE ON sites
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();


CREATE TABLE IF NOT EXISTS site_logs (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    traffic_light TEXT,
    http_status INTEGER,
    latency_ms INTEGER,
    ping_ms DOUBLE PRECISION,
    ssl_days_left INTEGER,
    dns_resolved BOOLEAN,
    redirects INTEGER,
    errors_last INTEGER,
    ping_interval INTEGER,
    raw_logs JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
