BEGIN;
SET LOCAL TIME ZONE 'UTC';

ALTER TABLE listing_lifecycle
    ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS price_status VARCHAR(10),
    ADD COLUMN IF NOT EXISTS price_basis VARCHAR(10),
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3),
    ADD COLUMN IF NOT EXISTS amount NUMERIC(18,2),
    ADD COLUMN IF NOT EXISTS price_vnd NUMERIC(18,0),
    ADD COLUMN IF NOT EXISTS price_changed_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_lc_price_status'
    ) THEN
        ALTER TABLE listing_lifecycle
            ADD CONSTRAINT chk_lc_price_status CHECK (
                price_status IS NULL
                OR price_status IN ('known', 'contact', 'negotiable')
            );
    END IF;
END;
$$;
WITH latest AS (
    SELECT DISTINCT ON (listing_key)
           listing_key, price_status, price_basis, currency, amount, price_vnd
    FROM listing_observation
    ORDER BY listing_key, run_started_at DESC, crawled_at DESC
), first_seen AS (
    SELECT listing_key, min(crawled_at) AS first_seen_at
    FROM listing_observation
    GROUP BY listing_key
)
UPDATE listing_lifecycle AS l
SET first_seen_at = f.first_seen_at,
    price_status  = o.price_status,
    price_basis   = o.price_basis,
    currency      = o.currency,
    amount        = o.amount,
    price_vnd     = o.price_vnd
FROM latest o
JOIN first_seen f USING (listing_key)
WHERE l.listing_key = o.listing_key
  AND l.first_seen_at IS NULL;
CREATE TABLE IF NOT EXISTS listing_status_event (
    listing_key TEXT NOT NULL,
    status VARCHAR(10) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    crawl_run_id TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_listing_status_event
        PRIMARY KEY (listing_key, occurred_at, status),
    CONSTRAINT chk_status_event_key CHECK (length(btrim(listing_key)) > 0),
    CONSTRAINT chk_status_event_status CHECK (status IN ('active', 'inactive'))
);
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'crawl_runs'
          AND column_name = 'lifecycle_applied_at'
    ) THEN
        ALTER TABLE crawl_runs ADD COLUMN lifecycle_applied_at TIMESTAMPTZ;
        UPDATE crawl_runs SET lifecycle_applied_at = now();
    END IF;
END;
$$;
COMMIT;
