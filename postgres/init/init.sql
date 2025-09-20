CREATE TABLE IF NOT EXISTS sites (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    name TEXT NOT NULL,
    com JSONB DEFAULT '{}'::jsonb,          -- любые дополнительные настройки
    last_traffic_light TEXT,                -- последний статус (green/orange/red)
    history JSONB DEFAULT '[]'::jsonb,      -- история последних проверок
    ping_interval INTEGER DEFAULT 30        -- частота проверки (в секундах)
);
