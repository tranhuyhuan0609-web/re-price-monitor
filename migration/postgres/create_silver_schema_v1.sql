BEGIN;
SET LOCAL TIME ZONE 'UTC';

-- =========================================================
-- 0. SHARED DOMAINS
-- =========================================================
CREATE DOMAIN nonblank_text AS TEXT
CHECK (length(btrim(VALUE)) > 0);

CREATE DOMAIN sha256_hex AS TEXT
CHECK (VALUE ~ '^[0-9a-f]{64}$');

-- =========================================================
-- 1. EVENT LEDGER
-- =========================================================
CREATE TABLE processed_raw_events (
    raw_event_id NONBLANK_TEXT NOT NULL PRIMARY KEY,
    run_started_at TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_event_run UNIQUE (raw_event_id, run_started_at)
);

CREATE TABLE listing_observation (
    raw_event_id NONBLANK_TEXT NOT NULL,
    crawl_run_id NONBLANK_TEXT NOT NULL,
    run_started_at TIMESTAMPTZ NOT NULL,
    crawled_at TIMESTAMPTZ NOT NULL,
    listing_key NONBLANK_TEXT NOT NULL,
    source NONBLANK_TEXT NOT NULL,
    source_listing_id TEXT,
    url NONBLANK_TEXT NOT NULL,
    url_hash SHA256_HEX NOT NULL,
    title NONBLANK_TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    price_status TEXT NOT NULL,
    price_basis TEXT NOT NULL,
    currency VARCHAR(3),
    amount NUMERIC(18,2),
    price_vnd NUMERIC(18,0),
    fx_rate NUMERIC(18,8),
    fx_rate_at TIMESTAMPTZ,
    price_per_m2 NUMERIC(18,0),
    property_type TEXT,
    area_m2 NUMERIC(12,2),
    bedrooms SMALLINT,
    bathrooms SMALLINT,
    year_built SMALLINT,
    address_raw TEXT,
    district TEXT,
    city TEXT,
    quality_flags TEXT[] NOT NULL DEFAULT '{}',
    processing_version INT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_listing_observation
        PRIMARY KEY (run_started_at, raw_event_id),
    CONSTRAINT uq_run_listing
        UNIQUE (run_started_at, crawl_run_id, listing_key),
    CONSTRAINT fk_observation_event
        FOREIGN KEY (raw_event_id, run_started_at)
        REFERENCES processed_raw_events (raw_event_id, run_started_at),
    CONSTRAINT chk_source
        CHECK (source = lower(btrim(source))),
    CONSTRAINT chk_source_listing_id
        CHECK (source_listing_id IS NULL OR length(btrim(source_listing_id)) > 0),
    CONSTRAINT chk_proc_version
        CHECK (processing_version > 0),
    CONSTRAINT chk_run_time
        CHECK (crawled_at >= run_started_at),
    CONSTRAINT chk_txn
        CHECK (transaction_type IN ('sale', 'rent')),
    CONSTRAINT chk_status
        CHECK (price_status IN ('known', 'contact', 'negotiable')),
    CONSTRAINT chk_basis
        CHECK (price_basis IN ('total', 'per_m2', 'per_month')),
    CONSTRAINT chk_ptype
        CHECK (property_type IS NULL OR property_type IN (
            'apartment', 'house', 'townhouse', 'villa',
            'land', 'commercial', 'other'
        )),
    CONSTRAINT chk_area
        CHECK (area_m2 IS NULL OR area_m2 > 0),
    CONSTRAINT chk_rooms
        CHECK ((bedrooms IS NULL OR bedrooms BETWEEN 0 AND 50) AND
               (bathrooms IS NULL OR bathrooms BETWEEN 0 AND 50)),
    CONSTRAINT chk_year
        CHECK (year_built IS NULL OR year_built BETWEEN 1800 AND 2100),
    CONSTRAINT chk_price_known
        CHECK (
            (price_status = 'known' AND
             amount IS NOT NULL AND amount > 0 AND
             price_vnd IS NOT NULL AND price_vnd > 0 AND
             currency IS NOT NULL AND currency ~ '^[A-Z]{3}$') OR
            (price_status IN ('contact', 'negotiable') AND
             amount IS NULL AND currency IS NULL AND
             price_vnd IS NULL AND fx_rate IS NULL AND
             fx_rate_at IS NULL)
        ),
    CONSTRAINT chk_fx
        CHECK (
            price_status <> 'known' OR (
                amount IS NOT NULL AND price_vnd IS NOT NULL AND
                currency IS NOT NULL AND (
                    (currency = 'VND' AND
                     amount = round(amount::NUMERIC(18,0)) AND
                     price_vnd::NUMERIC(18,0) = amount::NUMERIC(18,0) AND
                     fx_rate IS NULL AND fx_rate_at IS NULL) OR
                    (currency <> 'VND' AND fx_rate IS NOT NULL AND
                     fx_rate > 0 AND fx_rate_at IS NOT NULL AND
                     abs(price_vnd - amount * fx_rate) <= 10)
                )
            )
        ),
    CONSTRAINT chk_sale_basis
        CHECK (NOT (transaction_type = 'sale' AND price_basis = 'per_month')),
    CONSTRAINT chk_ppm2
        CHECK (
            price_per_m2 IS NULL OR (
                transaction_type = 'sale' AND price_status = 'known' AND
                price_per_m2 > 0 AND (
                    (price_basis = 'total' AND area_m2 IS NOT NULL AND
                     area_m2 > 0 AND
                     price_per_m2 = round(price_vnd / area_m2)) OR
                    (price_basis = 'per_m2' AND price_per_m2 = price_vnd)
                )
            )
        )
) PARTITION BY RANGE (run_started_at);

CREATE INDEX idx_obs_listing
ON listing_observation (listing_key, run_started_at DESC);

-- =========================================================
-- 3. SILVER: LISTING LIFECYCLE
-- =========================================================
CREATE TABLE listing_lifecycle (
    listing_key NONBLANK_TEXT NOT NULL PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'active',
    missing_count INT NOT NULL DEFAULT 0,
    last_seen_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_lc_status
        CHECK (status IN ('active', 'inactive')),
    CONSTRAINT chk_lc_state
        CHECK (
            (status = 'active' AND missing_count BETWEEN 0 AND 4 AND
             ended_at IS NULL) OR
            (status = 'inactive' AND missing_count >= 5 AND
             ended_at IS NOT NULL AND ended_at >= last_seen_at)
        )
);

-- =========================================================
-- 4. PARTITION MANAGEMENT
-- =========================================================
CREATE OR REPLACE FUNCTION create_observation_partition(month_start DATE)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    part_name TEXT;
    p_start TIMESTAMPTZ;
    p_end TIMESTAMPTZ;
    existing REGCLASS;
BEGIN
    IF month_start IS NULL OR
       month_start <> date_trunc('month', month_start)::DATE THEN
        RAISE EXCEPTION 'month_start must be the first day of a month: %',
            month_start;
    END IF;

    part_name := 'listing_observation_' || to_char(month_start, 'YYYY_MM');
    p_start := month_start::TIMESTAMP AT TIME ZONE 'UTC';
    p_end := (month_start + INTERVAL '1 month')::DATE::TIMESTAMP
        AT TIME ZONE 'UTC';
    existing := to_regclass(part_name);

    IF existing IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_inherits
            WHERE inhparent = 'listing_observation'::REGCLASS AND
                  inhrelid = existing
        ) THEN
            RAISE EXCEPTION
                '% already exists but is not a partition of listing_observation',
                part_name;
        END IF;
        RETURN;
    END IF;

    EXECUTE format(
        'CREATE TABLE %I PARTITION OF listing_observation ' ||
        'FOR VALUES FROM (%L) TO (%L)',
        part_name, p_start, p_end
    );
END;
$$;

CREATE OR REPLACE FUNCTION ensure_observation_partitions(
    months_ahead INT DEFAULT 2
)
RETURNS VOID LANGUAGE plpgsql AS $$
DECLARE
    first_month DATE := date_trunc('month', now() AT TIME ZONE 'UTC')::DATE;
    i INT;
BEGIN
    IF months_ahead IS NULL OR months_ahead NOT BETWEEN 0 AND 24 THEN
        RAISE EXCEPTION 'months_ahead must be between 0 and 24';
    END IF;

    FOR i IN 0..months_ahead LOOP
        PERFORM create_observation_partition(
            (first_month + make_interval(months => i))::DATE
        );
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION drop_observation_partition(
    month_start DATE,
    min_age_months INT DEFAULT 3
)
RETURNS BIGINT LANGUAGE plpgsql AS $$
DECLARE
    part_name TEXT;
    part_oid REGCLASS;
    cutoff DATE;
    n BIGINT;
BEGIN
    IF min_age_months IS NULL OR min_age_months < 1 THEN
        RAISE EXCEPTION 'min_age_months must be >= 1';
    END IF;

    IF month_start IS NULL OR
       month_start <> date_trunc('month', month_start)::DATE THEN
        RAISE EXCEPTION 'month_start must be the first day of a month: %',
            month_start;
    END IF;

    cutoff := (
        date_trunc('month', now() AT TIME ZONE 'UTC') -
        make_interval(months => min_age_months)
    )::DATE;

    IF month_start >= cutoff THEN
        RAISE EXCEPTION
            'Only partitions before month % may be dropped; requested: %',
            cutoff, month_start;
    END IF;

    part_name := 'listing_observation_' || to_char(month_start, 'YYYY_MM');
    part_oid := to_regclass(part_name);

    IF part_oid IS NULL THEN
        RAISE EXCEPTION 'Partition % does not exist', part_name;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_inherits
        WHERE inhparent = 'listing_observation'::REGCLASS AND
              inhrelid = part_oid
    ) THEN
        RAISE EXCEPTION '% is not a partition of listing_observation',
            part_name;
    END IF;

    EXECUTE format('SELECT count(*) FROM %I', part_name) INTO n;
    EXECUTE format('DROP TABLE %I', part_name);
    RETURN n;
END;
$$;

SELECT ensure_observation_partitions(2);
COMMIT;
