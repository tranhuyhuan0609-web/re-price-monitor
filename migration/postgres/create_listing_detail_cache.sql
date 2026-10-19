CREATE TABLE IF NOT EXISTS crawler_listing_detail_cache (
    site_id TEXT NOT NULL,
    listing_key TEXT NOT NULL,
    listing_url TEXT NOT NULL,
    description TEXT,
    contact_info TEXT,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_outcome TEXT NOT NULL DEFAULT 'pending'
        CHECK (last_outcome IN ('pending', 'success', 'failed')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (site_id, listing_key),
    CHECK (length(btrim(site_id)) > 0),
    CHECK (length(btrim(listing_key)) > 0),
    CHECK (length(btrim(listing_url)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_listing_detail_cache_last_attempt
    ON crawler_listing_detail_cache (site_id, last_attempt_at DESC);
