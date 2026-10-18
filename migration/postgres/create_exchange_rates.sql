CREATE TABLE IF NOT EXISTS exchange_rates (
    base_currency VARCHAR(3) NOT NULL,
    quote_currency VARCHAR(3) NOT NULL,
    rate NUMERIC(18, 8) NOT NULL CHECK (rate > 0),
    rate_at TIMESTAMPTZ NOT NULL,
    rate_type TEXT NOT NULL DEFAULT 'sell',
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_url TEXT,
    raw_payload JSONB,
    PRIMARY KEY (base_currency, quote_currency, rate_at, rate_type),
    CHECK (rate_type IN ('buy', 'sell', 'mid')),
    CHECK (base_currency <> quote_currency)
);

ALTER TABLE exchange_rates
    ADD COLUMN IF NOT EXISTS rate_type TEXT NOT NULL DEFAULT 'sell',
    ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS source_url TEXT,
    ADD COLUMN IF NOT EXISTS raw_payload JSONB;

CREATE UNIQUE INDEX IF NOT EXISTS uq_exchange_rates_type
    ON exchange_rates (base_currency, quote_currency, rate_at, rate_type);

CREATE INDEX IF NOT EXISTS idx_exchange_rates_type_lookup
    ON exchange_rates (base_currency, quote_currency, rate_type, rate_at DESC);
